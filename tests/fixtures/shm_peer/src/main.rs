use std::{
    env, thread,
    time::{Duration, Instant},
};

use anyhow::{bail, Context, Result};
use iceoryx2::prelude::*;
use serde_json::json;

fn main() -> Result<()> {
    let mut args = env::args().skip(1);
    let input = args.next().context("missing input service")?;
    let output = args.next().context("missing output service")?;
    let payload = args.next().context("missing payload")?.into_bytes();
    let node = NodeBuilder::new().create::<ipc::Service>()?;
    let input_name = input.as_str().try_into()?;
    let input_service = node
        .service_builder(&input_name)
        .publish_subscribe::<[u8]>()
        .enable_safe_overflow(true)
        .subscriber_max_buffer_size(2)
        .open_or_create()?;
    let publisher = input_service
        .publisher_builder()
        .initial_max_slice_len(4 * 1024 * 1024)
        .allocation_strategy(AllocationStrategy::PowerOfTwo)
        .create()?;
    let output_name = output.as_str().try_into()?;
    let deadline = Instant::now() + Duration::from_secs(10);
    let (output_service, subscriber) = loop {
        match node
            .service_builder(&output_name)
            .publish_subscribe::<[u8]>()
            .subscriber_max_buffer_size(2)
            .open()
        {
            Ok(service) => match service.subscriber_builder().create() {
                Ok(subscriber) => break (service, subscriber),
                Err(_) if Instant::now() < deadline => thread::sleep(Duration::from_millis(20)),
                Err(error) => bail!("failed to create output subscriber: {error:?}"),
            },
            Err(_) if Instant::now() < deadline => thread::sleep(Duration::from_millis(20)),
            Err(error) => bail!("failed to open output service: {error:?}"),
        }
    };
    let burst: Vec<Vec<u8>> = (0..16)
        .map(|index| format!("burst-{index:02}").into_bytes())
        .collect();
    for value in burst.iter().chain(std::iter::once(&payload)) {
        publisher
            .loan_slice_uninit(value.len())?
            .write_from_fn(|index| value[index])
            .send()?;
    }
    let deadline = Instant::now() + Duration::from_secs(10);
    let observed = loop {
        if output_service.dynamic_config().number_of_publishers() > 0 {
            if let Some(sample) = subscriber.receive()? {
                let value = sample.payload().to_vec();
                if value == payload {
                    break value;
                }
            }
        }
        if Instant::now() >= deadline {
            bail!("timed out waiting for echoed SHM payload");
        }
        thread::sleep(Duration::from_millis(5));
    };
    println!(
        "KT_SHM_PEER={}",
        json!({"payload_bytes": observed.len(), "burst_sent": burst.len(), "safe_overflow": true})
    );
    Ok(())
}

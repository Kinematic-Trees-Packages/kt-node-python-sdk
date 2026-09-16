import os
import resource
import tempfile
import unittest
from pathlib import Path

from ktnode.vision import decode_image_sample_summary, encode_image_sample, make_rgb_image, vision_sample_schema


class VisionContractTests(unittest.TestCase):
    def test_make_rgb_image_builds_contract_from_explicit_pixels(self):
        image = make_rgb_image(
            bytes([0, 0, 0, 1, 0, 1, 2, 0, 2, 3, 0, 3]),
            source="opencv-video-file",
            frame_number=0,
            width=4,
            height=1,
            captured_unix_ns=123,
        )
        self.assertEqual(image.data_shape, [1, 4, 3])
        self.assertEqual(image.frame_number, 0)
        self.assertEqual(list(image.data[:12]), [0, 0, 0, 1, 0, 1, 2, 0, 2, 3, 0, 3])

    def test_image_sample_flatbuffer_round_trip(self):
        image = make_rgb_image(
            bytes([0, 0, 0, 1, 0, 1, 2, 0, 2, 3, 0, 3]),
            source="opencv-video-file",
            frame_number=0,
            width=4,
            height=1,
            captured_unix_ns=123,
        )
        payload = encode_image_sample(image)
        summary = decode_image_sample_summary(payload)
        self.assertEqual(summary["source"], image.source)
        self.assertEqual(summary["frame_number"], 0)
        self.assertEqual(summary["data_shape"], [1, 4, 3])
        self.assertEqual(summary["data_prefix"], list(image.data[:12]))
        self.assertEqual(summary["compression"], summary["compression_raw"])
        self.assertEqual(summary["image_type"], summary["image_type_rgb"])
        self.assertEqual(summary["pipeline"], summary["pipeline_other"])
        self.assertEqual(summary["captured_unix_ns"], 123)

    def test_empty_and_malformed_image_payloads_are_rejected(self):
        for payload in (b"", b"VSM1", b"\x00" * 64):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                decode_image_sample_summary(payload)

    def test_large_vision_round_trip_is_exact_and_memory_bounded(self):
        width, height = 1920, 1080
        pixels = bytes(range(256)) * ((width * height * 3 + 255) // 256)
        pixels = pixels[: width * height * 3]
        before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        image = make_rgb_image(
            pixels,
            source="fixture/1080p",
            frame_number=42,
            width=width,
            height=height,
            captured_unix_ns=987_654_321,
        )
        payload = encode_image_sample(image)
        summary = decode_image_sample_summary(payload)
        after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        self.assertEqual(summary["data_shape"], [height, width, 3])
        self.assertEqual(summary["data_length"], len(pixels))
        self.assertEqual(summary["data_prefix"], list(pixels[:12]))
        self.assertEqual(summary["captured_unix_ns"], 987_654_321)
        self.assertLessEqual(after - before, 96 * 1024)

    def test_make_rgb_image_rejects_incomplete_contract(self):
        with self.assertRaises(ValueError):
            make_rgb_image(b"abc", source="camera", frame_number=0)
        with self.assertRaises(ValueError):
            make_rgb_image(b"abc", source="", frame_number=0, width=1, height=1)
        with self.assertRaises(ValueError):
            make_rgb_image(b"abc", source="camera", frame_number=-1, width=1, height=1)

    def test_schema_discovery_uses_composed_env_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema = root / "vision" / "vision_sample.fbs"
            schema.parent.mkdir()
            schema.write_text("root_type ImageSample;\n")
            old = os.environ.get("KT_NODE_SCHEMA_PATH")
            os.environ["KT_NODE_SCHEMA_PATH"] = str(root)
            try:
                self.assertEqual(vision_sample_schema(), schema)
            finally:
                if old is None:
                    os.environ.pop("KT_NODE_SCHEMA_PATH", None)
                else:
                    os.environ["KT_NODE_SCHEMA_PATH"] = old


if __name__ == "__main__":
    unittest.main()

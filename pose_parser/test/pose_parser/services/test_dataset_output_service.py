import unittest
import shutil
import pose_parser.utils.pickler as pickler

from pose_parser.services.video_data_dataloop_merge_service import (
    VideoDataDataloopMergeService,
)
from pose_parser.services.dataset_output_transformer_service import (
    DatasetOutputTransformerService,
)


class TestDatasetOutputTransformerService(unittest.TestCase):
    def setUp(self) -> None:
        self.annotations_directory = "./source_annotations"
        self.source_videos = "./source_videos"
        self.output_data_path = "./data/generated_datasets"
        self.output_keypoints_path = "./data/keypoints"
        test_dataset_path = "./test_dataset"
        # vdms = VideoDataDataloopMergeService(
        #     annotations_directory=self.annotations_directory,
        #     video_directory=self.source_videos,
        #     output_data_path=self.output_data_path,
        #     output_keypoints_path=self.output_keypoints_path,
        # )
        # vdms.create_video_annotation_map()
        # self.dataset = vdms.generate_dataset_from_map(limit=2)
        try:
            dataset = pickler.load_from_pickle(test_dataset_path)
            self.dataset = dataset
        except:
            vdms = VideoDataDataloopMergeService(
                annotations_directory=self.annotations_directory,
                video_directory=self.source_videos,
                output_data_path=self.output_data_path,
                output_keypoints_path=self.output_keypoints_path,
            )
            vdms.create_video_annotation_map()
            self.dataset = vdms.generate_dataset_from_map(limit=10)
            pickler.save_to_pickle(self.dataset, test_dataset_path)

        return super().setUp()

    def tearDown(self) -> None:
        # cleanup
        try:
            shutil.rmtree(self.output_data_path)
            shutil.rmtree(self.output_keypoints_path)
        except:
            return super().tearDown()
        return super().tearDown()

    def test_format_dataset(self):
        opts = {
            "include_joints": False,
            "include_angles": True,
            "include_distances": False,
            "include_normalized_points": False,
            "include_z_axis": False,
            "decimal_precision": 4,
            "merge_labels": True,
            "save_to_csv": True,
        }
        dots = DatasetOutputTransformerService(opts=opts)
        dataset = dots.format_dataset(generated_raw_dataset=self.dataset)

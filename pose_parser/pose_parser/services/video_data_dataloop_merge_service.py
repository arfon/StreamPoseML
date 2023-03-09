import glob
import os
import json
import time
from pathlib import Path

from pose_parser.services.dataloop_annotation_transformer_service import (
    DataloopAnnotationTransformerService,
    DataloopAnnotationTransformerServiceError,
)

from pose_parser.services.video_data_service import (
    VideoDataService,
    VideoDataServiceError,
)


class VideoDataDataloopMergeService:
    """Merge Dataloop annotations with video data.

    This class is responsible for searching an annotations directory to find
    relevant annotations for a specified video
    """

    annotations_directory: str
    video_directory: str
    output_data_path: str
    output_keypoints_path: str
    annotation_video_map: dict
    video_annotation_map: dict
    merged_data: dict

    def __init__(
        self,
        annotations_directory: str,
        video_directory: str,
        output_data_path: str,
        output_keypoints_path: str,
    ) -> None:
        """Upon initialization set data source directories and initialize storage dicts.

        Args:
            annotations_directory: str
                where do the source annotations live?
            video_directory: str
                where do the source videos live?
            output_data_path: str
                where to save the merged data
            output_keypoints_path: str
                where to put keypoint data
        """
        self.annotations_directory = annotations_directory
        self.video_directory = video_directory
        self.output_data_path = output_data_path
        self.output_keypoints_path = (output_keypoints_path,)
        self.annotation_video_map = {}
        self.video_annotation_map = {}
        self.merged_data = {}

    def create_video_annotation_map(self):
        """This method reads from the annotations and videos directory to
        create a file path map between videos and annotations.

        Returns:
            success: bool
                Returns: True if operation completes successfully

        Raises:
            exception: VideoDataDataloopMergeServiceError
                Raises:d if there's an error creating this map
        """
        try:
            annotation_files = [
                annotation
                for annotation in glob.iglob(
                    self.annotations_directory + "/**/*.json", recursive=True
                )
            ]
            # TODO support more than WEBM
            video_files = [
                video
                for video in glob.iglob(
                    self.video_directory + "/**/*.webm", recursive=True
                )
            ]

            for annotation_path in annotation_files:
                # load dataloop file and grab source filename
                filename = Path(json.load(open(annotation_path))["filename"]).stem
                for video_path in video_files:
                    if filename in video_path:
                        self.annotation_video_map[annotation_path] = video_path
                        self.video_annotation_map[video_path] = annotation_path

            return True
        except:
            raise VideoDataDataloopMergeServiceError(
                "There was an error creating the annotation video map"
            )

    def generate_dataset_from_map(
        self, limit: int = None, write_to_file: bool = False
    ) -> dict:
        """Use this object's generated map to create a nested dataset

        This method is reponsible for calling the video data service
        based on the map and merging the returned data into a dataset
        using the corresponding annotation

        Args:
            limit: int
                if there's a limit passed, only process up to this many annotations
        Returns:
            merged_data: dict
                If successful return the merged data from all source videos and annotations
        Raises:
            exception: VideoDataDataloopMergeServiceError

        """
        try:
            vds = VideoDataService()
            transformer = DataloopAnnotationTransformerService()
            process_counter = 0
            for annotation, video in self.annotation_video_map.items():
                if process_counter == limit:
                    break
                annotation_data = json.load(open(annotation))

                video_data = vds.process_video(
                    input_filename=os.path.basename(video),
                    video_input_path=os.path.split(video)[0],
                    output_data_path=self.output_keypoints_path,
                    write_to_file=False,
                    key_off_frame_number=False,
                    configuration={},
                )

                segmented_data = transformer.segment_video_data_with_annotations(
                    video_data=video_data, dataloop_data=annotation_data
                )
                self.merge_segmented_data(segmented_data=segmented_data)
                process_counter += 1

                if write_to_file:
                    self.write_merged_data_to_file()

            return self.merged_data
        except DataloopAnnotationTransformerServiceError:
            raise VideoDataDataloopMergeServiceError(
                "There was an error processing dataset due to the annotation transformer service"
            )
        except VideoDataServiceError:
            raise VideoDataDataloopMergeServiceError(
                "There was an error processing dataset due to the VideoDataService"
            )

    def write_merged_data_to_file(self) -> bool:
        """
        This method is responsible for writing the contents of the merged data dictionary to a json file

        Returns:
            success: bool
                True if operation was successful
        Raises:
            exception: VideoDataDataloopMergeServiceError
        """
        try:
            Path(self.output_data_path).mkdir(parents=True, exist_ok=True)
            merged_data_json = json.dumps(self.merged_data, indent=4)
            with open(
                os.path.join(
                    self.output_data_path, f"combined_dataset_{time.time_ns()}.json"
                ),
                "w",
            ) as outfile:
                outfile.write(merged_data_json)
            return True
        except:
            raise VideoDataDataloopMergeServiceError(
                "Error outputting JSON for merged data."
            )

    def merge_segmented_data(self, segmented_data: dict) -> None:
        """
        This method takes a segmented data dictionary and merges it into the class's merged data dictionary

        Args:
            segmented_data: dict
                A dictionary keyed off annotation labels containing a list of frame data dictionaries representing all the frames for a labeled clip of video
        Raises:
            exception: VideoDataDataloopMergeServiceError
        """
        try:
            for label, examples in segmented_data.items():
                if (label not in self.merged_data) or (
                    not bool(self.merged_data[label])
                ):
                    self.merged_data[label] = []
                for example in examples:
                    self.merged_data[label].append(example)
        except:
            raise VideoDataDataloopMergeServiceError(
                "There was an issue merging segmented data"
            )


class VideoDataDataloopMergeServiceError(Exception):
    """Raised when there's a problem in the VideoDataDatloopMergeService class"""

    pass

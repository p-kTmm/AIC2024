import argparse
import multiprocessing as mp
import os
import time
import cv2
import tqdm
import sys
import json
from detectron2.config import get_cfg
from detectron2.data.detection_utils import read_image
from detectron2.utils.logger import setup_logger

# Add the path to the CenterNet2 module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'third_party/CenterNet2/projects/CenterNet2/'))

from centernet.config import add_centernet_config

from grit.config import add_grit_config

from grit.predictor import VisualizationDemo
# constants
WINDOW_NAME = "GRiT"


def setup_cfg(args):
    cfg = get_cfg()
    # if args.cpu:
    #     cfg.MODEL.DEVICE="cpu"
    cfg.MODEL.DEVICE="cuda"
    add_centernet_config(cfg)
    add_grit_config(cfg)
    cfg.merge_from_file(args.config_file)
    cfg.merge_from_list(args.opts)
    # Set score_threshold for builtin models
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = args.confidence_threshold
    cfg.MODEL.PANOPTIC_FPN.COMBINE.INSTANCES_CONFIDENCE_THRESH = args.confidence_threshold
    if args.test_task:
        cfg.MODEL.TEST_TASK = args.test_task
    cfg.MODEL.BEAM_SIZE = 1
    cfg.MODEL.ROI_HEADS.SOFT_NMS_ENABLED = False
    cfg.USE_ACT_CHECKPOINT = False
    cfg.freeze()
    return cfg


def get_parser():
    parser = argparse.ArgumentParser(description="Detectron2 demo for builtin configs")
    parser.add_argument(
        "--config-file",
        default="",
        metavar="FILE",
        help="path to config file",
    )
    parser.add_argument("--cpu", action='store_true', help="Use CPU only.")
    parser.add_argument(
        "--input",
        nargs="+",
        help="A list of space separated input images; "
        "or a single glob pattern such as 'directory/*.jpg'",
    )
    parser.add_argument(
        "--output",
        help="A file or directory to save output visualizations. "
        "If not given, will show output in an OpenCV window.",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.4,
        help="Minimum score for instance predictions to be shown",
    )
    parser.add_argument(
        "--test-task",
        type=str,
        default='',
        help="Choose a task to have GRiT perform",
    )
    parser.add_argument(
        "--opts",
        help="Modify config options using the command-line 'KEY VALUE' pairs",
        default=[],
        nargs=argparse.REMAINDER,
    )
    return parser


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    args = get_parser().parse_args()
    setup_logger(name="fvcore")
    logger = setup_logger()
    logger.info("Arguments: " + str(args))

    cfg = setup_cfg(args)

    demo = VisualizationDemo(cfg)

    if args.input:
        for path in tqdm.tqdm(os.listdir(args.input[0]), disable=not args.output):
            img = read_image(os.path.join(args.input[0], path), format="BGR")
            start_time = time.time()
            predictions, visualized_output, bbox = demo.run_on_image(img)

            if args.output:
                json_file = {}
                predict_object = bbox.pred_object_descriptions.data
                predict_box = bbox.pred_boxes
                if not os.path.exists(args.output):
                    os.mkdir(args.output)
                if os.path.isdir(args.output):
                    assert os.path.isdir(args.output), args.output
                    out_filename = os.path.join(args.output, os.path.basename(path))
                    if "png" in out_filename:
                        out_filename = out_filename.replace("png", "json")
                    if "jpg" in out_filename:
                        out_filename = out_filename.replace("jpg", "json")
                for (name, box) in zip(predict_object, predict_box):
                    if name not in json_file:
                        json_file[name] = [box.tolist()]
                    else:
                        json_file[name].append(box.tolist())
                with open(out_filename, "w") as outfile:
                    json.dump(json_file, outfile)
            else:
                cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
                cv2.imshow(WINDOW_NAME, visualized_output.get_image()[:, :, ::-1])
                if cv2.waitKey(0) == 27:
                    break  # esc to quit

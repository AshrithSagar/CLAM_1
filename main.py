"""
main.py
Train the model
"""

import argparse
import math
import os
import pdb

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml
from torch.utils.data import DataLoader, sampler

from modules.core_utils import train
from modules.dataset_generic import (
    Generic_MIL_Dataset,
    Generic_WSI_Classification_Dataset,
)
from modules.file_utils import load_pkl, save_pkl
from modules.utils import *

# Generic training settings
# Configurations for WSI Training

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Patchify images")
    parser.add_argument("-c", "--config", type=str, help="Path to the config file")

    args = parser.parse_args()
    if args.config:
        config = yaml.safe_load(open(args.config, "r"))
        args = config["main"]


def seed_torch(seed=7):
    import random

    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)  # if you are using multi-GPU.
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


# ------------------------------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
seed_torch(args["seed"])

encoding_size = 1024
settings = {
    "k": args["k"],
    "k_start": args["k_start"],
    "k_end": args["k_end"],
    "task": args["task"],
    "max_epochs": args["max_epochs"],
    "results_dir": args["results_dir"],
    "lr": args["lr"],
    "experiment": args["exp_code"],
    "reg": args["reg"],
    "label_frac": args["label_frac"],
    "bag_loss": args["bag_loss"],
    "seed": args["seed"],
    "model_type": args["model_type"],
    "model_size": args["model_size"],
    "use_drop_out": args["drop_out"],
    "weighted_sample": args["weighted_sample"],
    "opt": args["opt"],
    "patch_dir": args["patch_dir"],
    "feat_dir": args["feat_dir"],
    "label_frac": args["label_frac"],
    "split_dir": args["split_dir"],
    "log_data": args["log_data"],
    "dataset_csv": args["dataset_csv"],
    "testing": args["testing"],
    "early_stopping": args["early_stopping"],
    "dropout": args["dropout"],
    "no_inst_cluster": args["no_inst_cluster"],
    "subtyping": args["subtyping"],
    "exp_code": args["exp_code"],
    "loss_weights": args["loss_weights"],
    "inst_loss": args["inst_loss"],
    "B": args["B"],
    "annot_dir": args["annot_dir"],
    "alpha_weight": args["alpha_weight"],
    "semi_supervised": args["semi_supervised"],
    "T1": args["T1"],
    "T2": args["T2"],
    "af": args["af"],
    "correction": args["correction"],
    "attention_labels_loss": args["attention_labels_loss"],
    "use_augmentation": args["use_augmentation"],
}
print("\nLoad Dataset")

exp_dir = os.path.join(
    settings["results_dir"], str(settings["exp_code"]) + "_s{}".format(settings["seed"])
)
if not os.path.isdir(exp_dir):
    os.mkdir(exp_dir)

with open(os.path.join(exp_dir, "config.yaml"), "w") as yaml_file:
    yaml.dump(config, yaml_file, default_flow_style=False)

# if args['split_dir'] is None:
#     args['split_dir'] = os.path.join('splits', args['task']+'_{}'.format(int(args['label_frac']*100)))
# else:
#     args['split_dir'] = os.path.join('splits', args['split_dir'])

# print('split_dir: ', split_dir)
# assert os.path.isdir(split_dir)

# settings.update({'split_dir': split_dir})


if args["task"] == "task_fungal_vs_nonfungal":
    args["n_classes"] = 2
    settings.update({"n_classes": args["n_classes"]})
    dataset = Generic_MIL_Dataset(
        csv_path=args["dataset_csv"],
        data_dir=args["feat_dir"],
        annot_dir=args["annot_dir"],
        results_dir=exp_dir,
        shuffle=False,
        seed=args["seed"],
        print_info=True,
        label_dict={"nonfungal": 0, "fungal": 1},
        patient_strat=False,
        ignore=[],
    )

elif task == "task_1_tumor_vs_normal":
    args["n_classes"] = 2
    settings.update({"n_classes": args["n_classes"]})
    dataset = Generic_MIL_Dataset(
        csv_path="dataset_csv/tumor_vs_normal_dummy_clean.csv",
        data_dir=os.path.join(args["data_root_dir"], "tumor_vs_normal_resnet_features"),
        shuffle=False,
        seed=args["seed"],
        print_info=True,
        label_dict={"normal_tissue": 0, "tumor_tissue": 1},
        patient_strat=False,
        ignore=[],
    )

elif task == "task_2_tumor_subtyping":
    args["n_classes"] = 3
    settings.update({"n_classes": args["n_classes"]})
    dataset = Generic_MIL_Dataset(
        csv_path="dataset_csv/tumor_subtyping_dummy_clean.csv",
        data_dir=os.path.join(args["data_root_dir"], "tumor_subtyping_resnet_features"),
        shuffle=False,
        seed=args["seed"],
        print_info=True,
        label_dict={"subtype_1": 0, "subtype_2": 1, "subtype_3": 2},
        patient_strat=False,
        ignore=[],
    )

    if model_type in ["clam_sb", "clam_mb"]:
        assert subtyping

else:
    raise NotImplementedError

with open(exp_dir + "/experiment_{}.txt".format(args["exp_code"]), "w") as f:
    print(settings, file=f)
f.close()

print("################# Settings ###################")
for key, val in settings.items():
    print("{}:  {}".format(key, val))


# ------------------------------------------------------
start = 0 if args["k_start"] == -1 else args["k_start"]
end = args["k"] if args["k_end"] == -1 else args["k_end"]

folds = np.arange(start, end)
final_metrics = {
    "folds": list(folds),
    "test_auc": [],
    "val_auc": [],
    "test_acc": [],
    "test_acc_2": [],
    "val_acc": [],
    "test_recall": [],
    "test_precision": [],
    # "cm_val": [], "cm_test": [],
    "test_specificity": [],
    "test_inst_acc": [],
    "test_inst_precision": [],
    "test_inst_recall": [],
    "test_inst_specificity": [],
}
for i in folds:
    seed_torch(args["seed"])
    train_dataset, val_dataset, test_dataset = dataset.return_splits(
        from_id=False,
        csv_path="{}/splits_{}.csv".format(args["split_dir"], i),
        use_augmentation=args["use_augmentation"],
    )

    datasets = (train_dataset, val_dataset, test_dataset)

    (
        results,
        CM_val,
        CM_test,
        cm_val_disp,
        cm_test_disp,
        fpr_val,
        tpr_val,
        fpr_test,
        tpr_test,
    ) = train(datasets, i, settings, final_metrics)

    # add f1-score based on precision and recall results
    # final_metrics["test_f1"].append(f1_score(
    #     final_metrics["test_precision"][-1],
    #     final_metrics["test_recall"][-1]
    # ))
    # final_metrics["test_inst_f1"].append(f1_score(
    #     final_metrics["test_inst_precision"][-1],
    #     final_metrics["test_inst_recall"][-1]
    # ))

    # write results to pkl
    filename = os.path.join(
        exp_dir, "splits_{}".format(i), "split_{}_results.pkl".format(i)
    )
    save_pkl(filename, results)

    plt.clf()
    filename = os.path.join(
        exp_dir, "splits_{}".format(i), "split_{}_ROC.png".format(i)
    )
    plt.title("ROC Curve")
    plt.plot(fpr_val, tpr_val, color="green")
    plt.plot(fpr_test, tpr_test, color="red")
    plt.xlabel("FPR (1 - Specificity)")
    plt.ylabel("TPR (Sensitivity)")
    plt.legend(("Validation", "Test"))
    plt.subplots_adjust(left=0.15)  # Tweak spacing to prevent clipping of ylabel
    plt.savefig(filename)

    ROC_data = {"val": [fpr_val, tpr_val], "test": [fpr_test, tpr_test]}
    filename = os.path.join(
        exp_dir, "splits_{}".format(i), "split_{}_ROC.pkl".format(i)
    )
    save_pkl(filename, ROC_data)

    plt.clf()
    cm_val_disp.plot()
    #     plt.imshow(plt.imread(cm_val_disp))
    filename = os.path.join(
        exp_dir, "splits_{}".format(i), "split_{}_CM_val.png".format(i)
    )
    plt.savefig(filename)

    plt.clf()
    cm_test_disp.plot()
    #     plt.imshow(plt.imread(cm_test_disp))
    filename = os.path.join(
        exp_dir, "splits_{}".format(i), "split_{}_CM_test.png".format(i)
    )
    plt.savefig(filename)

    CM_data = {"val": CM_val, "test": CM_test}
    filename = os.path.join(exp_dir, "splits_{}".format(i), "split_{}_CM.pkl".format(i))
    save_pkl(filename, CM_data)

final_df = pd.DataFrame(final_metrics)
mean_df = final_df.mean(axis=0).to_frame().T.drop("folds", axis=1)
std_df = final_df.std(axis=0).to_frame().T.drop("folds", axis=1)
final_mean_std = pd.concat([mean_df, std_df], ignore_index=True, sort=False)

if len(folds) != args["k"]:
    save_name = "summary_partial_{}_{}.csv".format(start, end)
else:
    save_name = "summary.csv"
final_df.to_csv(os.path.join(exp_dir, save_name), index=False)
final_mean_std.to_csv(os.path.join(exp_dir, "summary_avg.csv"), index=False)

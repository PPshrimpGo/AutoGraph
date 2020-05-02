from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data
from feature_engineer import dim_reduction, feature_generation

def fix_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True


# todo: profile the data loading
def generate_pyg_data(data):
    x = data['fea_table']
    if x.shape[1] == 1:
        x = x.to_numpy()
        x = x.reshape(x.shape[0])
        x = np.array(pd.get_dummies(x))
    else:
        x = x.drop('node_index', axis=1).to_numpy()

    x = torch.tensor(x, dtype=torch.float)

    df = data['edge_file']
    edge_index = df[['src_idx', 'dst_idx']].to_numpy()
    edge_index = sorted(edge_index, key=lambda d: d[0])
    edge_index = torch.tensor(edge_index, dtype=torch.long).transpose(0, 1)

    edge_weight = df['edge_weight'].to_numpy()
    edge_weight = torch.tensor(edge_weight, dtype=torch.float32)

    num_nodes = x.size(0)
    y = torch.zeros(num_nodes, dtype=torch.long)
    inds = data['train_label'][['node_index']].to_numpy()
    train_y = data['train_label'][['label']].to_numpy()
    y[inds] = torch.tensor(train_y, dtype=torch.long)

    train_indices = data['train_indices']
    test_indices = data['test_indices']

    data = Data(x=x, edge_index=edge_index, y=y, edge_weight=edge_weight)

    data.num_nodes = num_nodes
    data.train_indices = train_indices
    data.test_indices = test_indices

    train_mask = torch.zeros(num_nodes, dtype=torch.bool)
    train_mask[train_indices] = 1
    data.train_mask = train_mask

    test_mask = torch.zeros(num_nodes, dtype=torch.bool)
    test_mask[test_indices] = 1
    data.test_mask = test_mask
    return data


def generate_pyg_data_feature_transform(data, use_dim_reduction=True, use_feature_generation=True, sparse_threshold=0.9,
                      pca_threshold=0.75):
    x = data['fea_table']

    df = data['edge_file']
    edge_index = df[['src_idx', 'dst_idx']].to_numpy()
    edge_index = sorted(edge_index, key=lambda d: d[0])
    edge_index = torch.tensor(edge_index, dtype=torch.long).transpose(0, 1)

    edge_weight = df['edge_weight'].to_numpy()
    edge_weight = torch.tensor(edge_weight, dtype=torch.float32)

    num_nodes = x.shape[0]
    y = torch.zeros(num_nodes, dtype=torch.long)
    inds = data['train_label'][['node_index']].to_numpy()
    train_y = data['train_label'][['label']].to_numpy()
    y[inds] = torch.tensor(train_y, dtype=torch.long)

    train_indices = data['train_indices']
    test_indices = data['test_indices']

    ###   feature engineering  ###
    if use_dim_reduction:
        x = dim_reduction(x, sparse_threshold, pca_threshold)

    if x.shape[1] == 1 and use_feature_generation:
        added_feature = feature_generation(x, edge_index)
        x = np.concatenate([x, added_feature], axis=1)

    x = torch.tensor(x, dtype=torch.float)

    data = Data(x=x, edge_index=edge_index, y=y, edge_weight=edge_weight)

    data.num_nodes = num_nodes
    data.train_indices = train_indices
    data.test_indices = test_indices

    train_mask = torch.zeros(num_nodes, dtype=torch.bool)
    train_mask[train_indices] = 1
    data.train_mask = train_mask

    test_mask = torch.zeros(num_nodes, dtype=torch.bool)
    test_mask[test_indices] = 1
    data.test_mask = test_mask
    return data



def get_performance(valid_info):
    # the larger, the better
    # naive implementation
    return -valid_info['logloss']+0.1*valid_info['accuracy']

def divide_data(data, split_rates):
    assert len(split_rates) == 3

    indices = np.array(data.train_indices)
    np.random.shuffle(indices)

    split_thred = []
    accumulated_rate = 0
    for r in split_rates:
        accumulated_rate += r
        split_thred.append(int(len(indices)*accumulated_rate/np.sum(split_rates)))

    train_indices = indices[:split_thred[0]]
    early_valid_indices = indices[split_thred[0]:split_thred[1]]
    final_valid_indices = indices[split_thred[1]:]

    train_mask = torch.zeros(data.num_nodes, dtype=torch.bool)
    train_mask[train_indices] = 1
    early_valid_mask = torch.zeros(data.num_nodes, dtype=torch.bool)
    early_valid_mask[early_valid_indices] = 1
    final_valid_mask = torch.zeros(data.num_nodes, dtype=torch.bool)
    final_valid_mask[final_valid_indices] = 1
    return train_mask, early_valid_mask, final_valid_mask


def hyperparam_space_tostr(hyperparam_space):
    hyperparam_space_str = '\n'
    for k, v in hyperparam_space.items():
        hyperparam_space_str = hyperparam_space_str + "%-15s: %s\n" % (k, v.desc())
    return hyperparam_space_str


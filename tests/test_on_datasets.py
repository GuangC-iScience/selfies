"""Lengthy tests that are run on testing data sets.
"""

import faulthandler
import os
import random

import pandas as pd
import pytest
from rdkit.Chem import MolFromSmiles, MolToSmiles

import selfies as sf
from selfies.encoder import _parse_smiles
from selfies.kekulize import BRANCH_TYPE, RING_TYPE, kekulize_parser

faulthandler.enable()

datasets = [
    ('130K_QM9.txt', 'smiles'),
    ('51K_NonFullerene.txt', 'smiles'),
    ('250k_ZINC.txt', 'smiles'),
    ('8k_Tox21.txt', 'smiles'),
    ('93k_PubChem_MUV_bioassay.txt', 'smiles')
]


@pytest.mark.parametrize("test_name, column_name", datasets)
def test_roundtrip_translation(test_name, column_name, dataset_samples):
    """Tests a roundtrip SMILES -> SELFIES -> SMILES translation of the
    SMILES examples in QM9, NonFullerene, Zinc, etc.
    """

    constraints = sf.get_semantic_constraints()
    constraints['N'] = 6
    sf.set_semantic_constraints(constraints)

    # file I/O
    curr_dir = os.path.dirname(__file__)
    test_path = os.path.join(curr_dir, 'test_sets', test_name)

    # make pandas reader
    N = sum(1 for _ in open(test_path)) - 1
    S = dataset_samples if (0 < dataset_samples <= N) else N
    skip = sorted(random.sample(range(1, N + 1), N - S))
    reader = pd.read_csv(test_path,
                         chunksize=10000,
                         header=0,
                         delimiter=' ',
                         skiprows=skip)

    # roundtrip testing
    for chunk in reader:
        for in_smiles in chunk[column_name]:

            selfies = sf.encoder(in_smiles)
            assert selfies is not None
            out_smiles = sf.decoder(selfies)

            assert is_same_mol(in_smiles, out_smiles)


@pytest.mark.parametrize("test_name, column_name", datasets)
def test_kekulize_parser(test_name, column_name, dataset_samples):
    """Tests the kekulization of SMILES, which is the first step of
    selfies.encoder().
    """

    # file I/O
    curr_dir = os.path.dirname(__file__)
    test_path = os.path.join(curr_dir, 'test_sets', test_name)

    # make pandas reader
    N = sum(1 for _ in open(test_path)) - 1
    S = dataset_samples if (0 < dataset_samples <= N) else 0
    skip = sorted(random.sample(range(1, N + 1), N - S))
    reader = pd.read_csv(test_path,
                         chunksize=10000,
                         header=0,
                         delimiter=' ',
                         skiprows=skip)

    # kekulize testing
    for chunk in reader:
        for smiles in chunk[column_name]:

            # build kekulized SMILES
            kekule_fragments = []

            for fragment in smiles.split("."):

                kekule_gen = kekulize_parser(_parse_smiles(fragment))

                k = []
                for bond, symbol, symbol_type in kekule_gen:
                    if symbol_type == BRANCH_TYPE:
                        bond = ''
                    k.append(bond)

                    if symbol_type == RING_TYPE and len(symbol) == 2:
                        k.append('%')
                    k.append(symbol)

                kekule_fragments.append(''.join(k))

            kekule_smiles = '.'.join(kekule_fragments)

            assert is_same_mol(smiles, kekule_smiles)


# Helper Methods

def is_same_mol(smiles1, smiles2):
    """Helper method that returns True if smiles1 and smiles2 correspond
    to the same molecule.
    """

    if smiles1 is None or smiles2 is None:
        return False

    m1 = MolFromSmiles(smiles1)
    m2 = MolFromSmiles(smiles2)

    if m1 is None or m2 is None:
        return False

    can1 = MolToSmiles(m1)
    can2 = MolToSmiles(m2)

    return can1 == can2

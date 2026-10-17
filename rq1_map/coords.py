"""Coordinate space handling: everything is analysed in MNI."""
import numpy as np
from nimare.utils import tal2mni


def to_mni(experiments, coordinates):
    """Coordinates with x, y, z in MNI; foci of experiments with space == 'TAL' are converted with
    NiMARE's Lancaster (tal2icbm) transform."""
    out = coordinates.reset_index(drop=True).copy()
    out[["x", "y", "z"]] = out[["x", "y", "z"]].astype(float)
    tal_ids = set(experiments.loc[experiments.space == "TAL", "exp_id"])
    rows = out.exp_id.isin(tal_ids).to_numpy()
    if rows.any():
        out.loc[rows, ["x", "y", "z"]] = tal2mni(out.loc[rows, ["x", "y", "z"]].to_numpy())
    return out


def outside_brain(coords_mni, mask_img):
    """Boolean array: True where a focus falls outside the mask or off its grid."""
    ijk = np.rint(np.linalg.inv(mask_img.affine) @ np.c_[coords_mni[["x", "y", "z"]].to_numpy(), np.ones(len(coords_mni))].T)[:3].T.astype(int)
    data = np.asarray(mask_img.dataobj)
    inside = np.all((ijk >= 0) & (ijk < data.shape), axis=1)
    out = ~inside
    out[inside] = data[tuple(ijk[inside].T)] == 0
    return out

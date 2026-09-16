"""Robust Feather / Arrow IPC reader with dictionary decoding.

Solves the Polars / Arrow dictionary-encoding compatibility issue where
legacy Arrow files contain dictionary-encoded categorical columns with
negative (-1) key indices or null sentinels that cause:
    ComputeError('The dictionary key must fit in a `usize`, but -1 does not')
"""

import logging
from pathlib import Path
from typing import Union
import polars as pl
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather

logger = logging.getLogger("flycast.brain.feather_reader")


def decode_arrow_column(col: Union[pa.Array, pa.ChunkedArray]) -> Union[pa.Array, pa.ChunkedArray]:
    """Decodes a dictionary-encoded column into plain primitive/string types.

    Safely masks any negative indices (legacy -1 null sentinels) or out-of-bounds indices.
    """
    if not pa.types.is_dictionary(col.type):
        return col

    # Fast path: attempt standard dictionary_decode
    try:
        return pc.dictionary_decode(col)
    except Exception as decode_err:
        logger.debug("Fast dictionary_decode encountered: %s. Using bounds-masked decode.", decode_err)

    # Fallback for legacy negative (-1) index sentinels or invalid bounds
    chunks = col.chunks if isinstance(col, pa.ChunkedArray) else [col]
    decoded_chunks = []

    for chunk in chunks:
        indices = chunk.indices
        dictionary = chunk.dictionary
        dict_len = len(dictionary)

        # Validity mask: index must be non-null, >= 0, and < dict_len
        is_in_bounds = pc.and_(
            pc.greater_equal(indices, 0),
            pc.less(indices, dict_len)
        )
        is_valid = pc.and_(is_in_bounds, pc.is_valid(indices))

        # Mask out-of-bounds / negative values to null
        masked_indices = pc.if_else(is_valid, indices, None)
        decoded_chunk = pc.take(dictionary, masked_indices)
        decoded_chunks.append(decoded_chunk)

    if isinstance(col, pa.ChunkedArray):
        return pa.chunked_array(decoded_chunks)
    return decoded_chunks[0]


def read_feather_safe(path: Union[str, Path]) -> pl.DataFrame:
    """Safely reads a Feather file using PyArrow, decoding all dictionary-encoded

    categorical columns and converting to Polars without IPC usize/-1 errors.
    """
    file_path = Path(path)
    logger.info("Safely reading Feather table via PyArrow: %s", file_path)

    arrow_table = feather.read_table(file_path)

    decoded_cols = {}
    for name, col in zip(arrow_table.column_names, arrow_table.columns):
        decoded_cols[name] = decode_arrow_column(col)

    clean_table = pa.table(decoded_cols)
    df = pl.from_arrow(clean_table)

    logger.info(
        "Loaded %s successfully (%d rows, %d columns). Schema: %s",
        file_path.name,
        df.height,
        df.width,
        {name: str(dtype) for name, dtype in df.schema.items()}
    )
    return df

import json
from typing import Any, Dict, List, Union

import numpy as np
from fastapi import Response
from pydantic import BaseModel


def json_dump(arg: Any, indent: int | None = None) -> str:
    arg = process_arg(arg)
    if isinstance(arg, str):
        return arg
    return json.dumps(arg, ensure_ascii=False, indent=indent)


def process_arg(
    arg: Any, _recur_time: int = 10
) -> Union[str, List[Any], Dict[str, Any], Any]:
    if _recur_time <= 0:
        return f"{arg}"

    if hasattr(arg, "__dict__"):
        arg = arg.__dict__

    # if isinstance(arg, pd.DataFrame):
    #     arg = arg.to_numpy()

    if isinstance(arg, BaseModel):
        arg = arg.__dict__

    if isinstance(arg, Response):
        arg = arg.__dict__

    if isinstance(arg, dict):
        new_arg = {}
        for k, v in arg.items():
            new_arg[k] = process_arg(v, _recur_time - 1)
        arg = new_arg

    elif isinstance(arg, list) or isinstance(arg, tuple):
        return [process_arg(v, _recur_time - 1) for v in arg]

    elif isinstance(arg, np.ndarray):
        arg = list(arg)
        return [process_arg(v, _recur_time - 1) for v in arg]

    elif isinstance(arg, np.number):
        arg = float(arg)

    # elif pd.isna(arg):
    #     arg = None

    # elif isinstance(arg, np.integer):
    #     arg = int(arg)

    else:
        arg = f"{arg}"

    return arg

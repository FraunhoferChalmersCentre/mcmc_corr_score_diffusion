from dataclasses import dataclass, asdict
from typing import Optional, Tuple
from pathlib import Path
import json
from datetime import datetime
from copy import deepcopy
from typing import Tuple, Union
import pickle
import random
import numpy as np
import torch as th


def test():
    cfg = SimulationConfig.from_json(Path.cwd() / "exp/configs/hmc.json")
    cfg.save(Path.cwd() / "results")
    print(cfg.mcmc_bounds, type(cfg.mcmc_bounds))


@dataclass
class SimulationConfig:
    name: str
    # Domain
    image_size: int
    num_channels: int
    # Diffusion
    diff_model: str
    class_cond: bool
    num_diff_steps: int
    num_respaced_diff_steps: int
    num_samples: int
    batch_size: int
    # Guidance
    classifier: str
    guid_scale: float
    # MCMC
    mcmc_method: Optional[str]
    mcmc_steps: Optional[int]
    # Value for disabling MCMC steps:
    mcmc_lower_t: Optional[int]
    # Dict that include all necessary information for step sizes of the MCMC method
    mcmc_stepsizes: Optional[dict]
    # Number of trapezoidal steps
    n_trapets: Optional[int]
    # Seed
    seed: Optional[int] = None
    # Meta
    save_traj: bool = False
    results_dir: Path = Path.cwd() / "results"

    @staticmethod
    def from_json(cfg_file_path: Path):
        with open(cfg_file_path) as cfg_file:
            cfg = json.load(cfg_file)
        cfg = SimulationConfig(**cfg)
        cfg.results_dir = Path(cfg.results_dir)
        cfg._validate()
        return cfg

    def _validate(self):
        if self.mcmc_method is not None:
            assert self.mcmc_stepsizes is not None
            assert isinstance(self.mcmc_stepsizes["load"], bool)
            if self.mcmc_stepsizes["load"]:
                assert self.mcmc_stepsizes["bounds"] is not None
            else:
                assert isinstance(self.mcmc_stepsizes["params"]["factor"], float) or isinstance(
                    self.mcmc_stepsizes["params"]["factor"], int
                )
                assert isinstance(self.mcmc_stepsizes["params"]["exponent"], float) or isinstance(
                    self.mcmc_stepsizes["params"]["exponent"], int
                )
                assert self.mcmc_stepsizes["beta_schedule"] is not None
            if self.mcmc_method == "la":
                assert isinstance(self.n_trapets, int)

    def save(self, sim_dir: Path):
        tmp_config = deepcopy(self)
        tmp_config.results_dir = str(tmp_config.results_dir)
        with open(sim_dir / "config.json", "w") as outfile:
            json.dump(asdict(tmp_config), outfile, indent=4, sort_keys=False)


def get_step_size(step_size_dir: Path, dataset_name: str, mcmc_method: str, mcmc_accept_bounds: str):
    # print("Warning: using steps from T_resp = 500")
    # steps = 500
    path = step_size_dir / f"{dataset_name}_{mcmc_method}_{mcmc_accept_bounds}.p"
    assert path.exists(), f"Step size file '{path}' not found"
    with open(path, "rb") as f:
        res = pickle.load(f)
    # We accidentally save the last index (which we then leave with a reverse step)
    # Therefore we include t=T in the dict, but it's not populated with a step size.
    extracted = [(int(t), x["step_sizes"][-1]) for t, x in res.items() if x["step_sizes"]]
    return dict(extracted)


def setup_results_dir(config: SimulationConfig, job_id: Optional[int]) -> Path:
    config.results_dir.mkdir(exist_ok=True, parents=True)
    if job_id is None:
        sim_id = f"{config.name}_{timestamp()}"
    else:
        sim_id = f"{config.name}_{job_id}"
    sim_dir = config.results_dir / sim_id
    sim_dir.mkdir(exist_ok=True)
    config.save(sim_dir)
    return sim_dir


def timestamp() -> str:
    return datetime.now().strftime("%y%m%d_%H%M")


if __name__ == "__main__":
    test()

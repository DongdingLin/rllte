# =============================================================================
# MIT License

# Copyright (c) 2023 Reinforcement Learning Evolution Foundation

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# =============================================================================


from typing import Callable

import gymnasium as gym
import numpy as np
from gymnasium.vector import AsyncVectorEnv, SyncVectorEnv
from gymnasium.wrappers import FrameStack, GrayScaleObservation, RecordEpisodeStatistics, ResizeObservation, TransformReward

from rllte.env.atari.wrappers import EpisodicLifeEnv, FireResetEnv, MaxAndSkipEnv, NoopResetEnv
from rllte.env.utils import TorchVecEnvWrapper


def make_atari_env(
    env_id: str = "Alien-v5",
    num_envs: int = 8,
    device: str = "cpu",
    seed: int = 1,
    frame_stack: int = 4,
    distributed: bool = False,
) -> gym.Env:
    """Build Atari environments.

    Args:
        env_id (str): Name of environment.
        num_envs (int): Number of environments.
        device (str): Device (cpu, cuda, ...) on which the code should be run.
        seed (int): Random seed.
        frame_stack (int): Number of stacked frames.
        distributed (bool): For `Distributed` algorithms, in which `SyncVectorEnv` is required
            and reward clip will be used before environment vectorization.

    Returns:
        The vectorized environment.
    """

    def make_env(env_id: str, seed: int) -> Callable:
        def _thunk():
            env = gym.make(env_id)
            if distributed:
                env = TransformReward(env, lambda reward: np.sign(reward))
            env = NoopResetEnv(env, noop_max=30)
            env = MaxAndSkipEnv(env, skip=frame_stack)
            env = EpisodicLifeEnv(env)
            if "FIRE" in env.unwrapped.get_action_meanings():
                env = FireResetEnv(env)

            env = GrayScaleObservation(env)
            env = ResizeObservation(env, shape=(84, 84))
            env = FrameStack(env, frame_stack)

            env.action_space.seed(seed)
            env.observation_space.seed(seed)

            return env

        return _thunk

    if "NoFrameskip-v4" not in env_id:
        env_id = "ALE/" + env_id
    envs = [make_env(env_id, seed + i) for i in range(num_envs)]

    if distributed:
        envs = SyncVectorEnv(envs)
    else:
        envs = AsyncVectorEnv(envs)
        envs = RecordEpisodeStatistics(envs)
        envs = TransformReward(envs, lambda reward: np.sign(reward))

    return TorchVecEnvWrapper(envs, device)

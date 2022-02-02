from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.utils import set_random_seed

from coopihc import autospace, StateElement, State, BasePolicy, Bundle
from coopihc.bundle.wrappers.Train import TrainGym, TrainGym2SB3ActionWrapper

import numpy
import gym

# [start-define-bundle]
from coopihczoo import SimplePointingTask, ConstantCDGain, CarefulPointer

task = SimplePointingTask(gridsize=31, number_of_targets=8)
unitcdgain = ConstantCDGain(1)

# The policy to be trained has the simple action set [-5,-4,-3,-2,-1,0,1,2,3,,4,5]
action_state = State()
action_state["action"] = StateElement(0, autospace([-5 + i for i in range(11)]))


user = CarefulPointer(override_policy=(BasePolicy, {"action_state": action_state}))
bundle = Bundle(task=task, user=user, assistant=unitcdgain)
observation = bundle.reset(turn=1)


# >>> print(observation)
# ----------------  -----------  -------------------------  ------------------------------------------
# game_info         turn_index   1                          Discr(4)
#                   round_index  0                          Discr(1)
# task_state        position     24                         Discr(31)
#                   targets      [ 4 12 13 16 20 21 23 25]  MultiDiscr[31, 31, 31, 31, 31, 31, 31, 31]
# user_state        goal         4                          Discr(31)
# user_action       action       -4                         Discr(11)
# assistant_action  action       [[1.]]                     Cont(1, 1)
# ----------------  -----------  -------------------------  ------------------------------------------

# [end-define-bundle]

# [start-define-traingym]

env = TrainGym(
    bundle,
    train_user=True,
    train_assistant=False,
)
obs = env.reset()
# >>> print(env.action_space)
# Dict(user_action:Discrete(3))
# >>> print(env.observation_space)
# Dict(turn_index:Discrete(4), round_index:Discrete(1000), position:Discrete(31), targets:MultiDiscrete([31 31 31 31 31 31 31 31]), goal:Discrete(31), user_action:Discrete(3), assistant_action:Box(1.0, 1.0, (1, 1), float32))
env.step({"user_action": 1})

# Use env_checker from stable_baselines3 to verify that the env adheres to the Gym API
from stable_baselines3.common.env_checker import check_env

check_env(env, warn=False)
# [end-define-traingym]


# [start-define-mywrappers]

TEN_EPSILON32 = 10 * numpy.finfo(numpy.float32).eps


class MyActionWrapper(gym.ActionWrapper):
    def __init__(self, env_action_dict):
        super().__init__(env_action_dict)

        self.action_space = gym.spaces.Box(
            low=(-0.5 + TEN_EPSILON32 - 5) / 11 * 2,
            high=(10.5 - TEN_EPSILON32 - 5) / 11 * 2,
            shape=(1,),
            dtype=numpy.float32,
        )

    def action(self, action):
        return {
            "user_action": int(
                numpy.around(action * 11 / 2 - TEN_EPSILON32, decimals=0)
            )
            + 5
        }

    def reverse_action(self, action):
        return numpy.array((action["user_action"] - 5.0) / 11.0 * 2).astype(
            numpy.float32
        )


class MyObservationWrapper(gym.ObservationWrapper):
    def __init__(self, env, *args, **kwargs):
        super().__init__(env, *args, **kwargs)
        self.observation_space = gym.spaces.Box(
            low=-0.5 + TEN_EPSILON32, high=30.5 - TEN_EPSILON32, shape=(2,)
        )

    def observation(self, observation):
        return numpy.array(
            [observation["position"], observation["goal"]], dtype=numpy.float32
        )

    def reverse_observation(self, observation):
        return {
            "position": numpy.around(observation[0], decimals=0),
            "goal": numpy.around(observation[1], decimals=0),
        }


from gym.wrappers import FilterObservation

modified_env = FilterObservation(env, ("position", "goal"))
modified_env = MyObservationWrapper(modified_env)
modified_env = MyActionWrapper(modified_env)
# >>> print(modified_env.action_space)
# Box(-0.9999997615814209, 0.9999997615814209, (1,), float32)

# >>> print(modified_env.observation_space)
# Box(-0.4999988079071045, 30.499998092651367, (2,), float32)


check_env(modified_env, warn=True)

# >>> modified_env.reset()
# array([ 2., 27.], dtype=float32)
# Check that modified_env and the bundle game state concord
# >>> print(modified_env.unwrapped.bundle.game_state)
# ----------------  -----------  -------------------------  ------------------------------------------
# game_info         turn_index   1                          Discr(4)
#                   round_index  0                          Discr(1)
# task_state        position     2                          Discr(31)
#                   targets      [ 6  8 11 14 15 24 27 30]  MultiDiscr[31, 31, 31, 31, 31, 31, 31, 31]
# user_state        goal         27                         Discr(31)
# user_action       action       -2                         Discr(11)
# assistant_action  action       [[1.]]                     Cont(1, 1)
# ----------------  -----------  -------------------------  ------------------------------------------


modified_env.step(
    0.99
)  # 0.99 is cast to +5, multiplied by CD gain of 1 = + 5 increment

# >>> modified_env.step(
# ...     0.99
# ... )
# (array([ 7., 27.], dtype=float32), -1.0, False, {'name': 'CoopIHC Bundle Bundle\nAssistant:\n  Inference Engine: BaseInferenceEngine\n  Name: ConstantCDGain\n  Observation Engine: RuleObservationEngine\n  Policy: BasePolicy\n  State: []\nTask:\n  Name: SimplePointingTask\n  State:\n  - position\n  - targets\nUser:\n  Inference Engine: BaseInferenceEngine\n  Name: CarefulPointer\n  Observation Engine: RuleObservationEngine\n  Policy: BasePolicy\n  State:\n  - goal\n'})

# >>> print(modified_env.unwrapped.bundle.game_state)
# ----------------  -----------  -------------------------  ------------------------------------------
# game_info         turn_index   1                          Discr(4)
#                   round_index  1                          Discr(1)
# task_state        position     7                          Discr(31)
#                   targets      [ 6  8 11 14 15 24 27 30]  MultiDiscr[31, 31, 31, 31, 31, 31, 31, 31]
# user_state        goal         27                         Discr(31)
# user_action       action       5                          Discr(11)
# assistant_action  action       [[1.]]                     Cont(1, 1)
# ----------------  -----------  -------------------------  ------------------------------------------


# [end-define-mywrappers]

# As an Alternative to MyActionWrapper, you can use this generic wrapper which will one-hot encode discrete spaces to continuous spaces. SB3 handles dict spaces fine, but will one-hot encode discrete spaces and the like to a box.

# [start-define-SB3wrapper]
sb3env = TrainGym2SB3ActionWrapper(env)
check_env(sb3env, warn=True)
# [end-define-SB3wrapper]


# ============= function to make env

# [start-make-env]
def make_env():
    def _init():

        task = SimplePointingTask(gridsize=31, number_of_targets=8)
        unitcdgain = ConstantCDGain(1)

        action_state = State()
        action_state["action"] = StateElement(0, autospace([-5 + i for i in range(11)]))

        user = CarefulPointer(
            override_policy=(BasePolicy, {"action_state": action_state})
        )
        bundle = Bundle(task=task, user=user, assistant=unitcdgain)
        observation = bundle.reset(turn=1)
        env = TrainGym(
            bundle,
            train_user=True,
            train_assistant=False,
        )

        modified_env = FilterObservation(env, ("position", "goal"))
        modified_env = MyObservationWrapper(modified_env)
        modified_env = MyActionWrapper(modified_env)
        return modified_env

    return _init


# [end-make-env]
# =============
# [start-train]
if __name__ == "__main__":
    env = SubprocVecEnv([make_env() for i in range(4)])
    # to track rewards on tensorboard
    from stable_baselines3.common.vec_env import VecMonitor

    env = VecMonitor(env, filename="tmp/log")
    model = PPO("MlpPolicy", env, verbose=1, tensorboard_log="./tb/")
    model.learn(total_timesteps=1e6)
    model.save("saved_model")
# [end-train]

from coopihc.base.StateElement import StateElement
from coopihc.base.Space import Numeric, CatSet

import numpy
import gymnasium as gym
import pettingzoo
from collections import OrderedDict
from abc import ABC, abstractmethod

import warnings


class TrainGym2SB3ActionWrapper(gym.ActionWrapper):
    """TrainGym2SB3ActionWrapper

    Wrapper that flatten all spaces to boxes, using one-hot encoding for discrete spaces.

    While this wrapper will likely work for all cases, it may sometimes be more effective to code your own actionwrapper to avoid one-hot encoding.

    :param gym: [description]
    :type gym: [type]
    """

    def __init__(self, env):
        super().__init__(env)

        self.action_space = gym.spaces.utils.flatten_space(self.env.action_space)

    def action(self, action):
        return gym.spaces.utils.unflatten(self.env.action_space, action)

    def reverse_action(self, action):
        return gym.spaces.utils.flatten(action)


class _GymnasiumBasedEnv:
    def __init__(
        self,
        bundle,
        *args,
        train_user=False,
        train_assistant=False,
        observation_dict=None,
        reset_dic={},
        reset_turn=None,
        filter_observation=None,
        **kwargs,
    ):
        self.wrapper_list = []
        self.bundle = bundle
        self.bundle.env = self
        self.observation_dict = observation_dict
        self.reset_dic = reset_dic
        self.filter_observation = filter_observation

        self._convertor = GymConvertor(filter_observation=self.filter_observation)

        # The asymmetry of these two should be resolved. Currently, some fiddling is needed due to Issue # 58 https://github.com/jgori-ouistiti/CoopIHC/issues/58 . It is expected that when issue 58 is resolved, this code can be cleaned up.
        self.action_space = self.get_action_space()
        self.observation_space = self.get_observation_space()

        # Below: Using ordereddict here is forced due to Open AI gym's behavior: when initializing the Dict space, it tries to order the dict by keys, which may change the order of the dict entries. This is actually useless since Python 3.7 because dicts are ordered by default.

    @property
    def user(self):
        return self.bundle.user

    @property
    def assistant(self):
        return self.bundle.assistant

    @property
    def task(self):
        return self.bundle.task

    def get_agent_observation_space(self, agent):
        obs_dic = OrderedDict({})

        observation = getattr(self.bundle, agent).observation
        for key, value in observation.filter(
            mode="stateelement", flat=True, filterdict=self.filter_observation
        ).items():
            obs_dic.update({key: self.convert_space(value)})

        return gym.spaces.Dict(obs_dic)

    def convert_space(self, object):
        if isinstance(object, StateElement):
            object = object.space
        return self._convertor.convert_space(object)


class GymWrapper(gym.Env, _GymnasiumBasedEnv):
    def __init__(
        self,
        bundle,
        train_user=False,
        train_assistant=False,
        observation_dict=None,
        reset_dic=None,
        reset_turn=None,
        filter_observation=None,
        **kwargs,
    ):
        self.train_user = train_user
        self.train_assistant = train_assistant

        if reset_turn is None:
            if self.train_user:
                self.reset_turn = 1
            if train_assistant:  # override reset_turn if train_assistant is True
                self.reset_turn = 3

        else:
            self.reset_turn = reset_turn

        _GymnasiumBasedEnv.__init__(
            bundle,
            observation_dict=observation_dict,
            reset_dic=reset_dic,
            reset_turn=reset_turn,
            filter_observation=filter_observation,
            **kwargs,
        )

    def get_action_space(self):
        """get_action_space

        Create a gym.spaces.Dict out of the action states of the Bundle.

        """
        # ----- Init Action space -------
        action_dict = OrderedDict({})
        if self.train_user:
            for key, value in self.bundle.user.action_state.filter(
                mode="stateelement"
            ).items():
                action_dict.update({"user_action__" + key: self.convert_space(value)})

        if self.train_assistant:
            for key, value in self.bundle.assistant.action_state.filter(
                mode="stateelement"
            ).items():
                action_dict.update(
                    {"assistant_action__" + key: self.convert_space(value)}
                )

        return gym.spaces.Dict(action_dict)

    def get_observation_space(self):
        """get_observation_space

        Same as get_action_space for observations.


        """
        self.bundle.reset(go_to=self.reset_turn)
        # ------- Init Observation space

        if self.train_user and self.train_assistant:
            raise NotImplementedError(
                "Currently this wrapper can not deal with simultaneous training of users and assistants."
            )

        if self.train_user:
            return self.get_agent_observation_space("user")
        if self.train_assistant:
            return self.get_agent_observation_space("assistant")

    def reset(self, seed=None, options=None):
        reset_kw = {
            "dic": self.reset_dic,
            "go_to": self.reset_turn,
            "seed": seed,
        }  # default dict
        if options is not None:
            reset_kw.update(options)

        self.bundle.reset(**reset_kw)
        if self.train_user and self.train_assistant:
            raise NotImplementedError
        if self.train_user:
            return self._convertor.filter_gamestate(self.bundle.user.observation), {
                "name": "CoopIHC Bundle {}".format(str(self.bundle))
            }
        if self.train_assistant:
            return (
                self._convertor.filter_gamestate(self.bundle.assistant.observation),
                {"name": "CoopIHC Bundle {}".format(str(self.bundle))},
            )

    def step(self, action):
        ### Code below should be changed, quick fix for now/
        user_action = action.get("user_action__action", None)
        if user_action is None and self.train_user:
            raise ValueError(
                "Error in step, the dictionary you have provided is not recognized --> should be user_action__action"
            )
        assistant_action = action.get("assistant_action__action", None)
        if assistant_action is None and self.train_assistant:
            raise ValueError(
                "Error in step, the dictionary you have provided is not recognized --> should be assistant_action__action"
            )
        ###################################################

        obs, rewards, flag = self.bundle.step(
            user_action=user_action, assistant_action=assistant_action
        )

        if self.train_user and self.train_assistant:
            raise NotImplementedError(
                "Wrong wrapper class. For a multi agent reinforcement learning environment, you should inherit from pettingzoo's AEC"
            )
        if self.train_user:
            obs = self._convertor.filter_gamestate(self.bundle.user.observation)
        if self.train_assistant:
            obs = self._convertor.filter_gamestate(self.bundle.assistant.observation)

        return (
            obs,
            float(sum(rewards.values())),
            flag,
            False,
            {"name": "CoopIHC Bundle {}".format(str(self.bundle))},
        )


class PettingZooWrapper(pettingzoo.utils.env.AECEnv, _GymnasiumBasedEnv):
    def __init__(
        self,
        *args,
        bundle,
        observation_dict=None,
        reset_dic=None,
        reset_turn=None,
        filter_observation=None,
        task_rewards_weights=[
            [1 / 2, 1 / 2],
            [1 / 2, 1 / 2],
        ],  # [[w_user_step_1, w_assistant_step_1] [w_user_step_2, w_assistant_step_2]]
        **kwargs,
    ):
        if (task_rewards_weights[0][0] + task_rewards_weights[0][1] != 1) or (
            task_rewards_weights[1][0] + task_rewards_weights[1][1] != 1
        ):
            warnings.warn(
                "Task rewards to not sum to 1. The task reward weights structure should be [[w_user_step_1, w_assistant_step_1] [w_user_step_2, w_assistant_step_2]]"
            )

        self.possible_agents = ["user", "assistant"]
        self.reset_turn = reset_turn
        _GymnasiumBasedEnv.__init__(
            bundle,
            observation_dict=observation_dict,
            reset_dic=reset_dic,
            reset_turn=reset_turn,
            filter_observation=filter_observation,
            **kwargs,
        )

    def get_action_space(self):
        """get_action_space

        Create a gym.spaces.Dict out of the action states of the Bundle.

        """
        # ----- Init Action space -------
        user_action_dict = {}

        for key, value in self.bundle.user.action_state.filter(
            mode="stateelement"
        ).items():
            user_action_dict.update({"user_action__" + key: self.convert_space(value)})

        assistant_action_dict = {}

        for key, value in self.bundle.assistant.action_state.filter(
            mode="stateelement"
        ).items():
            assistant_action_dict.update(
                {"assistant_action__" + key: self.convert_space(value)}
            )

        return {"user": user_action_dict, "assistant": assistant_action_dict}

    def get_observation_space(self):
        """get_observation_space

        Same as get_action_space for observations.


        """
        self.bundle.reset(go_to=self.reset_turn)

        return gym.spaces.Dict(
            {
                "user": self.get_agent_observation_space("user"),
                "assistant": self.get_agent_observation_space("assistant"),
            }
        )

    def reset(self, seed=None, options=None):
        reset_kw = {
            "dic": self.reset_dic,
            "go_to": self.reset_turn,
            "seed": seed,
        }  # default dict
        if options is not None:
            reset_kw.update(options)

        self.agents = copy(self.possible_agents)
        self.bundle.reset(**reset_kw)

        observation = {
            a: getattr(
                getattr(self._convertor.filter_gamestate(self.bundle, a), "observation")
            )
            for a in self.agents
        }

        return observation, {
            a: {"name": "CoopIHC Bundle {}".format(str(self.bundle))}
            for a in self.agents
        }

    def step(self, action):
        ### Code below should be changed, quick fix for now/
        user_action = action.get("user_action__action", None)
        if user_action is None and self.train_user:
            raise ValueError(
                "Error in step, the dictionary you have provided is not recognized --> should be user_action__action"
            )
        assistant_action = action.get("assistant_action__action", None)
        if assistant_action is None and self.train_assistant:
            raise ValueError(
                "Error in step, the dictionary you have provided is not recognized --> should be assistant_action__action"
            )
        ###################################################

        obs, rewards, flag = self.bundle.step(
            user_action=user_action, assistant_action=assistant_action
        )

        user_obs = self._convertor.filter_gamestate(self.bundle.user.observation)
        assistant_obs = self._convertor.filter_gamestate(
            self.bundle.assistant.observation
        )

        obs = {"user": user_obs, "assistant": assistant_obs}
        rewards = {
            "user": rewards["user_observation_reward"]
            + rewards["user_inference_reward"]
            + rewards["user_policy_reward"]
            + self.task_rewards_weights[0][0] * rewards["first_task_reward"]
            + task_rewards_weights[1][0] * rewards["second_task_reward"],
            "assistant": rewards["assistant_observation_reward"]
            + rewards["assistant_inference_reward"]
            + rewards["assistant_policy_reward"]
            + self.task_rewards_weights[0][1] * rewards["first_task_reward"]
            + task_rewards_weights[1][1] * rewards["second_task_reward"],
        }

        flag = {a: flag for a in self.agents}
        termination = {a: False for a in self.agents}
        infos = {
            a: {"name": "CoopIHC Bundle {}".format(str(self.bundle))}
            for a in self.agents
        }

        if flag:
            self.agents = []

        return (obs, rewards, flag, termination, infos)


class GymWrapper(gym.Env):
    """Generic Wrapper to make bundles compatibles with gym.Env

    This is a Wrapper to make a Bundle compatible with gym.Env. Read more on the Train class.


    :param bundle: bundle to convert to a gym.Env
    :type bundle: `Bundle <coopihc.bundle.Bundle.Bundle>`
    :param train_user: whether to train the user, defaults to True
    :type train_user: bool, optional
    :param train_assistant: whether to train the assistant, defaults to True
    :type train_assistant: bool, optional
    :param observation_dict: to filter out observations, you can apply a dictionnary, defaults to None. e.g.:

    .. code-block:: python

        filterdict = OrderedDict(
            {
                "user_state": OrderedDict({"goal": 0}),
                "task_state": OrderedDict({"x": 0}),
            }
        )

    You can always filter out observations later using an ObservationWrapper. Difference in performance between the two approaches is unknown.

    .. note::

        This wrapper only works currently for single actions for agent labeled "action" i.e. the agent's action state looks like this:             ``action_state = State({'action': array_element(...)})``

    :type observation_dict: collections.OrderedDict, optional
    :param reset_dic: During training, the bundle will be repeatedly reset. Pass the reset_dic here if needed (see Bundle reset mechanism), defaults to {}
    :type reset_dic: dict, optional
    :param reset_turn: During training, the bundle will be repeatedly reset. Pass the reset_turn here (see Bundle reset_turn mechanism), defaults to None, which selects either 1 if the user is trained else 3
    :type reset_turn: int, optional
    """

    def __init__(
        self,
        bundle,
        *args,
        train_user=False,
        train_assistant=False,
        observation_dict=None,
        reset_dic={},
        reset_turn=None,
        filter_observation=None,
        **kwargs,
    ):
        self.wrapper_list = []

        self.train_user = train_user
        self.train_assistant = train_assistant
        self.bundle = bundle
        self.bundle.env = self
        self.observation_dict = observation_dict
        self.reset_dic = reset_dic
        self.filter_observation = filter_observation

        if reset_turn is None:
            if self.train_user:
                self.reset_turn = 1
            if train_assistant:  # override reset_turn if train_assistant is True
                self.reset_turn = 3

        else:
            self.reset_turn = reset_turn

        self._convertor = GymConvertor(filter_observation=filter_observation)

        # The asymmetry of these two should be resolved. Currently, some fiddling is needed due to Issue # 58 https://github.com/jgori-ouistiti/CoopIHC/issues/58 . It is expected that when issue 58 is resolved, this code can be cleaned up.
        self.action_space = self.get_action_space()
        self.observation_space = self.get_observation_space()

        # Below: Using ordereddict here is forced due to Open AI gym's behavior: when initializing the Dict space, it tries to order the dict by keys, which may change the order of the dict entries. This is actually useless since Python 3.7 because dicts are ordered by default.

    @property
    def user(self):
        return self.bundle.user

    @property
    def assistant(self):
        return self.bundle.assistant

    @property
    def task(self):
        return self.bundle.task

    def get_action_space(self):
        """get_action_space

        Create a gym.spaces.Dict out of the action states of the Bundle.

        """
        # ----- Init Action space -------
        action_dict = OrderedDict({})
        if self.train_user:
            for key, value in self.bundle.user.action_state.filter(
                mode="stateelement"
            ).items():
                action_dict.update({"user_action__" + key: self.convert_space(value)})

        if self.train_assistant:
            for key, value in self.bundle.assistant.action_state.filter(
                mode="stateelement"
            ).items():
                action_dict.update(
                    {"assistant_action__" + key: self.convert_space(value)}
                )

        return gym.spaces.Dict(action_dict)

    def get_observation_space(self):
        """get_observation_space

        Same as get_action_space for observations.


        """
        self.bundle.reset(go_to=self.reset_turn)
        # ------- Init Observation space

        if self.train_user and self.train_assistant:
            raise NotImplementedError(
                "Currently this wrapper can not deal with simultaneous training of users and assistants."
            )

        if self.train_user:
            return self.get_agent_observation_space("user")
        if self.train_assistant:
            return self.get_agent_observation_space("assistant")

    def get_agent_observation_space(self, agent):
        obs_dic = OrderedDict({})

        observation = getattr(self.bundle, agent).observation
        for key, value in observation.filter(
            mode="stateelement", flat=True, filterdict=self.filter_observation
        ).items():
            obs_dic.update({key: self.convert_space(value)})

        return gym.spaces.Dict(obs_dic)

    def reset(self, seed=None, options=None):
        reset_kw = {
            "dic": self.reset_dic,
            "go_to": self.reset_turn,
            "seed": seed,
        }  # default dict
        if options is not None:
            reset_kw.update(options)

        self.bundle.reset(**reset_kw)
        if self.train_user and self.train_assistant:
            raise NotImplementedError
        if self.train_user:
            return self._convertor.filter_gamestate(self.bundle.user.observation), {
                "name": "CoopIHC Bundle {}".format(str(self.bundle))
            }
        if self.train_assistant:
            return (
                self._convertor.filter_gamestate(self.bundle.assistant.observation),
                {"name": "CoopIHC Bundle {}".format(str(self.bundle))},
            )

    def step(self, action):
        ### Code below should be changed, quick fix for now/
        user_action = action.get("user_action__action", None)
        if user_action is None and self.train_user:
            raise ValueError(
                "Error in step, the dictionary you have provided is not recognized --> should be user_action__action"
            )
        assistant_action = action.get("assistant_action__action", None)
        if assistant_action is None and self.train_assistant:
            raise ValueError(
                "Error in step, the dictionary you have provided is not recognized --> should be assistant_action__action"
            )
        ###################################################

        obs, rewards, flag = self.bundle.step(
            user_action=user_action, assistant_action=assistant_action
        )

        if self.train_user and self.train_assistant:
            raise NotImplementedError
        if self.train_user:
            obs = self._convertor.filter_gamestate(self.bundle.user.observation)
        if self.train_assistant:
            obs = self._convertor.filter_gamestate(self.bundle.assistant.observation)

        return (
            obs,
            float(sum(rewards.values())),
            flag,
            False,
            {"name": "CoopIHC Bundle {}".format(str(self.bundle))},
        )

    def convert_space(self, object):
        if isinstance(object, StateElement):
            object = object.space
        return self._convertor.convert_space(object)

    def render(self, mode):
        """See Bundle and gym API

        :meta public:
        """
        self.bundle.render(mode)

    def close(self):
        """See Bundle and gym API

        :meta public:
        """
        self.bundle.close()


class RLConvertor(ABC):
    """RLConvertor

    An object, who should be subclassed that helps convert spaces from Bundles to another library.

    :param interface: API target for conversion, defaults to "gym"
    :type interface: str, optional
    """

    def __init__(self, interface="gym", **kwargs):
        self.interface = interface
        if self.interface != "gym":
            raise NotImplementedError

    @abstractmethod
    def convert_space(self, space):
        pass

    @abstractmethod
    def filter_gamestate(self, gamestate, observation_mapping):
        pass


class GymConvertor(RLConvertor):
    """GymConvertor

    Convertor to convert spaces from Bundle to Gym.

    .. note::

        Code is a little messy. Refactoring together with Train and TrainGym would be beneficial.

    :param RLConvertor: [description]
    :type RLConvertor: [type]
    """

    def __init__(self, filter_observation=None, **kwargs):
        super().__init__(interface="gym", **kwargs)
        self._filter_observation = filter_observation

    def convert_space(self, space):
        if isinstance(space, Numeric):
            return gym.spaces.Box(
                low=numpy.atleast_1d(space.low),
                high=numpy.atleast_1d(space.high),
                dtype=space.dtype,
            )
        elif isinstance(space, CatSet):
            return gym.spaces.Discrete(space.N)

    def filter_gamestate(self, gamestate):
        """filter_gamestate

        converts a CoopIHC observation to a valid Gym observation


        """

        dic = gamestate.filter(
            mode="array-Gym", filterdict=self._filter_observation, flat=True
        )

        return dic


def apply_wrappers(action, wrapped_env):
    """

    In rl_sb3.py, you can check that this works, after having defined the env:

    .. code-block:: python

        action = bundle.user.policy.sample()[0]
        from coopihc.bundle.wrappers.Train import apply_wrappers

        gym_action = apply_wrappers(action, modified_env)
    """
    action_wrappers = []
    while True:
        action_w = getattr(wrapped_env, "action", None)
        if action_w is not None:
            action_wrappers.append(wrapped_env)
        wrapped_env = getattr(wrapped_env, "env", None)
        if wrapped_env is None:
            break

    for _action_w in action_wrappers[::-1]:
        action = _action_w.reverse_action(action)

    return action


class WrapperReferencer:
    """Reference Wrappers for Train objects

    When applying wrappers (e.g. Gym wrappers) to ``Train`` objects, the ``Train`` object does not have a reference to those wrappers (from a wrapped environment called ``env``, you can access the ``Train`` object) by doing ``env.unwrapped``, but there is no way to access the lis of wrappers from the ``Train`` object.
    To make the reference, simply make sure your wrapper subclasses WrapperReferencer as well. For example:

    .. code-block:: python

        class AssistantActionWrapper(ActionWrapper, WrapperReferencer):
            def __init__(self, env):
                ActionWrapper.__init__(self, env)
                WrapperReferencer.__init__(self, env)
                _as = env.action_space["assistant_action__action"]
                self.action_space = Box(low=-1, high=1, shape=_as.shape, dtype=np.float32)
                self.low, self.high = _as.low, _as.high
                self.half_amp = (self.high - self.low) / 2
                self.mean = (self.high + self.low) / 2

            def action(self, action):
                return {"assistant_action__action": int(action * self.half_amp + self.mean)}

            def reverse_action(self, action):
                raw = action["assistant_action__action"]
                return (raw - self.mean) / self.half_amp

    This will add a ``wrapper_list`` attribute to the ``Train`` object.

    Doing this is required to use an agent's predict method with ``wrappers=True``.


    """

    def __init__(self, env):
        self.env.unwrapped.wrapper_list.append(self)

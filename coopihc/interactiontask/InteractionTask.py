from abc import ABC, abstractmethod
from coopihc.space.State import State
from coopihc.space.StateElement import StateElement

"""
    The main API methods for this class are:

        __init__

        finit

        reset

        user_step

        assistant_step

        render

    :meta public:
    """


class InteractionTask(ABC):
    """InteractionTask

    The class that defines an Interaction Task. Subclass this task when creating a new task to ensure compatibility with CoopIHC. When doing so, make sure to call ``super()`` in ``__init__()``.

    """

    def __init__(self):

        self._state = State()
        self.bundle = None
        self.round = 0
        self.timestep = 0.1

        # Render
        self.ax = None

    def finit(self):
        return

    @property
    def turn_number(self):
        """Turn number.

        The turn number of the game

        :return: turn number
        :rtype: numpy.ndarray
        """
        return self.bundle.turn_number

    @property
    def state(self):
        """state

        The current state of the task.

        :return: task state
        :rtype: :py:class:`State<coopihc.space.State.State>`
        """
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def user_action(self):
        """user action

        The last action input by the user.

        :return: user action
        :rtype: :py:class:`State<coopihc.space.State.State>`
        """
        if self.bundle:
            return self.bundle.game_state["user_action"]["action"]

    @property
    def assistant_action(self):
        """assistant action

        The last action input by the assistant.

        :return: assistant action
        :rtype: :py:class:`State<coopihc.space.State.State>`
        """
        if self.bundle:
            return self.bundle.game_state["assistant_action"]["action"]

    def __content__(self):
        """Custom class representation.

        A custom class representation.

        :return: custom repr
        :rtype: dictionnary
        """
        return {
            "Name": self.__class__.__name__,
            "State": self.state.__content__(),
        }
        """Describe how the task state should be reset. This method has to be redefined when subclassing this class.

        :param args: (OrderedDict) state to which the task should be reset, if provided.

        :return: state (OrderedDict) of the task.

        :meta public:
        """

    def _base_reset(self, dic=None):
        """base reset

        Method that wraps the user defined reset() method. Takes care of the dictionnary reset mechanism and updates rounds.

        :param dic: reset dictionnary (passed by bundle),
        :type dic: dictionnary, optional
        """
        self.round = 0

        if not dic:
            self.state.reset(dic={})
            self.reset(dic=dic)
            return

        self.reset(dic=dic)
        for key in list(self.state.keys()):
            value = dic.get(key)
            if isinstance(value, StateElement):
                value = value["values"]
            if value is not None:
                self.state[key]["values"] = value

    def base_user_step(self, *args, **kwargs):
        """base user step

        Wraps the user defined user_step() method. For now does little but provide default values, may be useful later.

        :return: (task state, task reward, is_done flag, metadata):
        :rtype: tuple(:py:class:`State<coopihc.space.State.State>`, float, boolean, dictionnary)
        """
        ret = self.user_step(*args, **kwargs)
        if ret is None:
            return self.state, -1 / 2, False, {}
        else:
            return ret

    def base_assistant_step(self, *args, **kwargs):
        """base assistant step

        Wraps the assistant defined assistant_step() method. For now does little but provide default values, may be useful later.

        :return: (task state, task reward, is_done flag, metadata):
        :rtype: tuple(:py:class:`State<coopihc.space.State.State>`, float, boolean, dictionnary)
        """
        ret = self.assistant_step(*args, **kwargs)
        if ret is None:
            return self.state, -1 / 2, False, {}
        else:
            return ret

    @abstractmethod
    def user_step(self, *args, **kwargs):
        """user_step

        Redefine this to specify the task state transitions and rewards issued.

        :return: (task state, task reward, is_done flag, {})
        :rtype: tuple(:py:class:`State<coopihc.space.State.State>`, float, boolean, dictionnary)
        """
        return None

    @abstractmethod
    def assistant_step(self, *args, **kwargs):
        """assistant_step

        Redefine this to specify the task state transitions and rewards issued.

        :return: (task state, task reward, is_done flag, {})
        :rtype: tuple(:py:class:`State<coopihc.space.State.State>`, float, boolean, dictionnary)
        """
        return None

    @abstractmethod
    def reset(self, dic=None):
        """reset

        Redefine this to specify how to reinitialize the task before each new game.

        .. warning::

            the method signature is likely outdated and should be reset(self) since the base_reset() method already accounts for the reset dic mechanism

        :param dic: [likely outdated], defaults to None
        :type dic: [type], optional
        :return: task state
        :rtype: :py:class:`State<coopihc.space.State.State>`
        """
        return None

    def render(self, *args, **kwargs):
        """Render the task on the main plot.

        :param mode: (str) text or plot
        :param args: (list) list of axis in order axtask, axuser, axassistant

        """
        mode = kwargs.get("mode")
        if mode is None:
            mode = "text"

        if "text" in mode:
            print(self.state)
        else:
            pass

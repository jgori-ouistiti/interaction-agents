import numpy
import matplotlib.pyplot as plt
from collections import OrderedDict
import gym
from core.interactiontask import InteractionTask


class SimplePointingTask(InteractionTask):
    """ A 1D pointing task.

    A 1D grid of size 'Gridsize'. The cursor is at a certain 'Position' and there are several potential 'Targets' on the grid. The operator action is modulated by the assistant.

    :param gridsize: (int) Size of the grid
    :param number_of_targets: (int) Number of targets on the grid

    :meta public:
    """
    def __init__(self, gridsize = 31, number_of_targets = 10):
        super().__init__()
        self.state = OrderedDict({'Gridsize': [gridsize], 'Position': [2], 'Targets': [3,4]})
        self.number_of_targets = 10

    def reset(self, *args):
        """ Reset the task.

        Reset the grid used for rendering, define new targets, select a starting position

        :param args: reset to the given state

        :meta public:
        """

        if args:
            raise NotImplementedError
        else:
            self.grid = [' ' for i in range(self.state['Gridsize'][0])]
            targets = sorted(numpy.random.choice(list(range(self.state['Gridsize'][0])), size = self.number_of_targets, replace = False))
            for i in targets:
                self.grid[i] = 'T'
            # Define starting position
            copy = list(range(len(self.grid)))
            for i in targets:
                copy.remove(i)
            position = int(numpy.random.choice(copy))
            self.state['Position'] = [position]
            self.state['Targets'] = targets


    def operator_step(self, operator_action):
        """ Do nothing, increment turns, return half a timestep

        :meta public:
        """
        return super().operator_step(operator_action)

    def assistant_step(self, assistant_action):
        """ Modulate the operator's action.

        Multiply the operator action with the assistant action.
        Update the position and grids.

        :param assistant_action: (list)

        :return: new state (OrderedDict), half a time step, is_done (True/False)

        :meta public:
        """
        super().assistant_step(assistant_action)
        is_done = False
        operator_action = self.bundle.assistant.state['OperatorAction'][0]
        assistant_action = assistant_action[0]
        self.state['Position'] = [int(numpy.clip(numpy.round(self.state['Position'][0] + operator_action*assistant_action, decimals = 0), 0, self.state['Gridsize'][0]-1))]
        if self.state['Position'][0] == self.bundle.operator.state['Goal'][0]:
            is_done = True
        return self.state, -1/2, is_done, {}

    def render(self, ax, *args, mode="text"):
        """ Render the task.

        Plot or print the grid, with cursor and target positions.

        :param ax:
        :param args:
        :param mode: 'text' or 'plot'

        .. warning::

            revisit the signature of this function

        :meta public:
        """
        goal = self.bundle.operator.state['Goal'][0]
        self.grid[goal] = 'G'
        if 'text' in mode:
            tmp = self.grid.copy()
            tmp[int(self.state['Position'][0])] = 'P'
            _str = "|"
            for t in tmp:
                _str += t + "|"

            print('\n')
            print("Turn number {:f}".format(self.turn))
            print(_str)

            targets = sorted(self.state['Targets'])
            print('Targets:')
            print(targets)
            print("\n")
        if 'plot' in mode:
            if self.ax is not None:
                self.update_position()
            else:
                self.ax = ax
                self.init_grid()
                self.ax.set_aspect('equal')
        if not ('plot' in mode or 'text' in mode):
            raise NotImplementedError


    def set_box(self, ax, pos, draw = "k", fill = None, symbol = None, symbol_color = None, shortcut = None):
        """ For Render.

        Draws box on the given axis ax at the given position pos, with a given style.

        :meta public:
        """
        if shortcut == 'void':
            draw = 'k'
            fill = '#aaaaaa'
            symbol = None
        elif shortcut == 'target':
            draw = '#96006c'
            fill = "#913979"
            symbol = "1"
            symbol_color = 'k'
        elif shortcut == 'goal':
            draw = '#009c08'
            fill = '#349439'
            symbol = "X"
            symbol_color = 'k'
        elif shortcut == 'position':
            draw = '#00189c'
            fill = "#6573bf"
            symbol = "X"
            symbol_color = 'k'

        BOX_SIZE = 1
        BOX_HW = BOX_SIZE / 2

        _x = [pos-BOX_HW, pos+BOX_HW, pos + BOX_HW, pos - BOX_HW]
        _y = [-BOX_HW, -BOX_HW, BOX_HW, BOX_HW]
        x_cycle = _x + [_x[0]]
        y_cycle = _y + [_y[0]]
        if fill is not None:
            fill = ax.fill_between(_x[:2], _y[:2], _y[2:], color = fill)

        draw, = ax.plot(x_cycle,y_cycle, '-', color = draw, lw = 2)
        symbol = None
        if symbol is not None:
            symbol = ax.plot(pos, 0, color = symbol_color, marker = symbol, markersize = 100)

        return draw, fill, symbol

    def init_grid(self):
        """ For Render.

        Draw grid.

        :meta public:
        """
        self.draws = []
        self.fills = []
        self.symbols = []
        for i in range(self.state['Gridsize'][0]):
            draw, fill, symbol = self.set_box(self.ax, i, shortcut = 'void')
            self.draws.append(draw)
            self.fills.append(fill)
            self.symbols.append(symbol)
        for t in self.state['Targets']:
            self.fills[t].remove()
            self.draws[t].remove()
            if self.symbols[t]:
                self.symbols[t].remove()
            draw, fill, symbol = self.set_box(self.ax, t, shortcut = 'target')
            self.draws[t] = draw
            self.fills[t] = fill
            self.symbols[t] = symbol
        t = self.bundle.operator.state['Goal'][0]
        self.fills[t].remove()
        self.draws[t].remove()
        if self.symbols[t]:
            self.symbols[t].remove()
        draw, fill, symbol = self.set_box(self.ax, t, shortcut = 'goal')
        self.draws[t] = draw
        self.fills[t] = fill
        self.symbols[t] = symbol

        self.draw_pos = self.state["Position"][0]
        self.update_position()



        self.ax.set_yticks([])
        self.ax.set_xticks(list(range(self.state['Gridsize'][0]))[::5])
        self.ax.set_xlim([-.6,self.state['Gridsize'][0] - .4])
        plt.show(block = False)

    def update_position(self):
        """ For Render.

        Update the plot, changing the cursor position.

        :meta public:
        """
        t = self.draw_pos
        self.fills[t].remove()
        self.draws[t].remove()
        if self.symbols[t]:
            self.symbols[t].remove()
        if t == self.bundle.operator.state['Goal'][0]:
            shortcut = 'goal'
        elif t in self.state['Targets']:
            shortcut = 'target'
        else:
            shortcut = 'void'
        draw, fill, symbol = self.set_box(self.ax, t, shortcut = shortcut)
        self.draws[t] = draw
        self.fills[t] = fill
        self.symbols[t] = symbol


        t = self.state['Position'][0]
        draw, fill, symbol = self.set_box(self.ax, t, shortcut = 'position')
        self.draws[t] = draw
        self.fills[t] = fill
        self.symbols[t] = symbol
        self.draw_pos = t


# class Continuous1DPointing(ClassicControlTask):
#     """ A 1D pointing task in Continuous space, unbounded, centered target
#
#     """
#
#     def __init__(self, I, b, ta, te):
#         a1 = b/(ta*te*I)
#         a2 = 1/(ta*te) + (1/ta + 1/te)*b/I
#         a3 = b/I + 1/ta + 1/te
#         bu = 1/(ta*te*I)
#
#
#         A = numpy.array([   [0, 1, 0, 0],
#                             [0, 0, 1, 0],
#                             [0, 0, 0, 1],
#                             [0, -a1, -a2, -a3]    ])
#
#         B = numpy.array([[ 0, 0, 0, bu]]).reshape((-1,1))
#
#         C = numpy.array([   [1, 0, 0, 0],
#                             [0, 1, 0, 0],
#                             [0, 0, 1, 0]
#                                 ])
#         super().__init__(4, .01, A, B, C)

# class CS_DT_Pointing(DT_ClassicControlTask):
#     """ A 1D pointing task in Continuous space, Discrete Time, with unbounded, centered target
#
#     """
#
#     def __init__(self, F, G, timestep = 0.1):
#
#
#
#         super().__init__(A.shape[1], timestep, A, B)



class Screen_v0(InteractionTask):
    def __init__(self, screen_size, number_of_targets):
        """ A 2D pointing.

        Clipping is enforced, no noise.



        :param screen_size: (list) [width, height] in pixels
        :param number_of_targets: (int) The number of targets that will be placed on the screen
        """
        # Task properties
        self.screen_size = screen_size
        self.number_of_targets = int(number_of_targets)
        self.max_cycle = 20
        self.timestep = 0.1
        self.target_radius = 20

        # Call super().__init__() before anything else
        super().__init__()

        # Define the state. You can put dummy values at this point.
        self.state = OrderedDict({'Screensize': screen_size, 'Position': [[100,100]], 'Targets': [(numpy.array(screen_size)/i).tolist() for i in range(self.number_of_targets)]})


        # Rendering stuff
        self.ax = None


    def render(self, *args, mode = 'plot'):
        axgame, axoperator, axassistant = args
        if self.ax is not None:
            self.update_position()
        else:
            self.ax = axgame
            self.init_grid(axoperator)
            self.ax.set_aspect('equal')
            plt.show(block = False)


    def init_grid(self, axoperator):
        targets = self.state['Targets']
        self.ax.set_xlim([-10 , 10 + self.screen_size[0]])
        self.ax.set_ylim([-10 , 10 + self.screen_size[1]])

        # draw screen edge
        self.ax.plot([0, self.screen_size[0], self.screen_size[0], 0, 0], [0,0, self.screen_size[1], self.screen_size[1], 0], lw = 1, color = 'k')

        for x,y in targets:
            circle = plt.Circle((x,y), self.target_radius, color = '#913979')
            self.ax.add_patch(circle)

        x,y = self.state['Position'][0]
        self.cursor =  plt.Circle((x,y), self.target_radius/5, color = 'r')
        self.ax.add_patch(self.cursor)
        cursor2 = plt.Circle((x,y), self.target_radius/5, color = 'r')
        axoperator.add_patch(cursor2)

    def update_position(self):
        self.cursor.remove()
        x,y = self.state['Position'][0]
        print(x,y)
        self.cursor =  plt.Circle((x,y), self.target_radius/5, color = 'r')
        self.ax.add_patch(self.cursor)




    def reset(self, *args):
        """ Randomly draw N+1 disjoint disks. The N first disks are used as targets, the last disk's center is used as cursor position.
        """

        # Place targets
        if args:
            raise NotImplementedError
        else:
            targets = []
            radius = self.target_radius
            while len(targets)  < self.number_of_targets + 1: # generate targets as well as a start position
                x,y = numpy.random.random(2)*numpy.array(self.screen_size)
                passed = True
                if x > radius and x < (self.screen_size[0] - radius) and y > radius and y < (self.screen_size[1] - radius):
                    if not targets:
                        targets = [[x,y]]
                    else:
                        for xt,yt in targets:
                            if (xt-x)**2 + (yt-y)**2 <= 4*radius**2:
                                passed = False
                        if passed:
                            targets.append([x,y])


            position = targets.pop(-1)
            targets.sort()

        # Place cursor
        if args:
            raise NotImplementedError
        else:
            pass

        self.state = OrderedDict()
        self.state['Position'] = [position]
        self.state['Targets'] = targets



    def operator_step(self, operator_action):
        self.bundle.assistant.state['OperatorAction'] = operator_action
        return super().operator_step(operator_action)

    def assistant_step(self, assistant_action):
        is_done = False

        # convert to array
        if not isinstance(assistant_action, numpy.ndarray):
            assistant_action = numpy.array(assistant_action)
        operator_action = self.bundle.assistant.state['OperatorAction']
        if not isinstance(operator_action, numpy.ndarray):
            operator_action = numpy.array(operator_action)


        # Apply modulation
        delta = assistant_action*operator_action
        self.state['Position'][0] = self.state['Position'][0] + delta

        # Clip (separate clipping means probably should not be going through arrays at all)
        self.state['Position'][0][0] = numpy.clip(self.state['Position'][0][0], self.target_radius/5,self.screen_size[0]-self.target_radius/5)
        self.state['Position'][0][1] = numpy.clip(self.state['Position'][0][1], self.target_radius/5,self.screen_size[1]-self.target_radius/5)

        ### Insert here is_done condition

        return self.state, -1/2, is_done, {}

    def render(self, axgame, axoperator, axassistant, mode):
        ax = axgame
        # goal = self.bundle.operator.state[0]
        if self.ax is not None:
            self.update_position()
        else:
            self.ax = ax
            self.init_grid(axoperator)
            self.ax.set_aspect('equal')
            plt.show(block = False)

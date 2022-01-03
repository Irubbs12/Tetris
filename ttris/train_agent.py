import tetris_ai
import heuristics as hu
import data
import neat
import pickle
from model import Population, LinearNet

class AI_Agent:
    def __init__(self, rows, columns):  # piece is an object
        self.rows = rows
        self.columns = columns
        self.field = [[0 for _ in range(self.columns)] for _ in range(self.rows)]
        self.landed = None
        self.final_cords = []
        self.heuris = hu.Heuristics(self.columns, self.rows)  # this is a heuristics obj
        self.best_move = None
        self.move_data = {}
        self.final_positions = {}
        self.all_pieces = ['I', 'S', 'O', 'Z', 'T', 'L', 'J']
        self.all_configurations_per_piece = {}
        self.all_configurations = {}
        self.cord_scores = {}
        self.actions_scores = []
        self.neural_network = None

    def get_possible_configurations(self):
        positions = [[(ind_y, ind_x) for ind_y in range(self.columns) if ind_x != 0 or ind_x != 1] for ind_x in range(self.rows)]
        all_positions = [tupl for li in positions for tupl in li]

        for piece_id in self.all_pieces:
            data_obj = data.Data(piece_id, None)
            all_configurations = {}

            for pos_x, pos_y in all_positions:
                all_configurations[(pos_x, pos_y)] = []
                for index in range(4):  # all rotation indices....
                    relative_cords = []
                    data_obj.rot_index = index
                    ascii_cords = data_obj.get_data()  # exp: [(0, 1), (0, 2), (1, 2), (1, 3)]

                    lowest_block = max(ascii_cords, key=lambda cord: cord[1])  # lowest hanging piece based on y

                    lo_x, lo_y = lowest_block
                    # get relative cords to lowest block
                    for x, y in ascii_cords:
                        relative_cords.append((x - lo_x, y - lo_y))

                    final_global_cords = [(x + pos_x, y + pos_y) for x, y in relative_cords]

                    # check validity of rotation states
                    if all([cord in all_positions for cord in final_global_cords]):
                        all_configurations[(pos_x, pos_y)].append((index, final_global_cords))

                # remove position from all configurations list if it yields an empty list i.e no configurations are
                # possible

                if len(all_configurations[(pos_x, pos_y)]) == 0:
                    del all_configurations[(pos_x, pos_y)]

            self.all_configurations_per_piece[piece_id] = all_configurations

    def final_y(self, column):
        for row in range(self.rows):
            if self.field[row][column] == 1:
                return row - 1
            else:
                continue

        return self.rows - 1

    def set_all_configurations(self, current_piece):
        self.all_configurations = self.all_configurations_per_piece[current_piece.str_id]

    def get_piece_mapping(self, current_piece):
        mapping = [0 for _ in range(7)]

        mapping[self.all_pieces.index(current_piece.str_id)] = 1

        return mapping

    def update_agent(self, current_piece):
        self.set_all_configurations(current_piece)
        self.update_all_configurations()
        self.update_field()

        self.heuris.update_field(self.field)

    def update_field(self):
        self.field = [[0 for _ in range(self.columns)] for _ in range(self.rows)]
        if self.landed != {}:
            for pos, val in self.landed.items():
                if val != (255, 255, 255):
                    x, y = pos
                    try:
                        self.field[y][x] = 1
                    except IndexError:
                        print('random index error is random')
                        pass

    def update_all_configurations(self):
        if self.landed != {}:
            for landed_cord in self.landed.keys():
                if landed_cord in self.all_configurations:
                    del self.all_configurations[landed_cord]

    def set_final_cords(self, final_cords):
        self.final_cords = final_cords

    def set_final_positions(self):
        self.final_positions = {}
        for cord in self.all_configurations:
            if cord in self.final_cords:
                self.final_positions[cord] = self.all_configurations[cord]

    def evaluation_function(self, current_piece):
        best_move_per_column = {}
        if len(self.final_positions) != 0:
            score_move_per_column = {}

            for cord, positions in self.final_positions.items():
                score_move_per_column[cord] = []
                for index, pos in positions:  # first part is the rotation index, second part are the positions
                    field = self.field.copy()

                    # fill in block positions in test field
                    for x, y in pos:
                        field[y][x] = 1

                    # pass that as the field to be used to get heuristics
                    self.heuris.update_field(field)

                    # access info from heuristics file
                    possible_reward = self.heuris.get_reward()
                    board_state = self.heuris.get_heuristics()

                    # get piece mapping
                    mapping = self.get_piece_mapping(current_piece)

                    # prepare full board state
                    full_board_state = board_state

                    # get score from nueral net
                    move_score = self.neural_network(full_board_state)[0]

                    # re-update with initial field!! IMPORTANT!!
                    self.heuris.update_field(self.field)

                    # check all positions above the piece, make sure they are empty, otherwise it is physically impossible for them to be there
                    if all([self.field[y_above][fin_x] == 0 for fin_x, fin_y in pos for y_above in range(fin_y) if (fin_x, y_above) not in pos]):
                        score_move_per_column[cord].append((index, cord, pos, possible_reward, move_score))

            # find best move per column
            for cord, positions in score_move_per_column.items():
                if len(positions) != 0:
                    best_move_per_column[cord] = max(positions, key = lambda x : x[-1])

            # go through each move per column score and choose highest scoring move

            best_move = max(best_move_per_column.items(), key= lambda pair: pair[1][-1])[1]

            self.best_move = best_move[:-1]

        else:
            self.best_move = current_piece.get_config()

    def get_best_move(self, current_piece):
        final_cords = [(col, self.final_y(col)) for col in range(self.columns)]
        self.set_final_cords(final_cords)
        self.set_final_positions()

        self.evaluation_function(current_piece)

        return self.best_move

    def print_field(self):
        for i in self.field:
            print(i)

epochs = 100
class Trainer:
    def __init__(self):
        self.agent = AI_Agent(tetris_ai.ROWS, tetris_ai.COLUMNS)
        self.agent.get_possible_configurations()
        self.old_population = None
        self.new_population = None
        self.best_fitness = 0

    def eval_genomes(self):
        for epoch in range(epochs):
            print(f'Epoch: {epoch}')
            print('========================================')
            self.new_population = Population(150, self.old_population)

            for nueral_net in range(self.new_population.size):
                print(f'Neural net at index {nueral_net}')
                current_fitness = 0
                tetris_game = tetris_ai.Tetris()

                self.agent = AI_Agent(tetris_ai.ROWS, tetris_ai.COLUMNS)
                self.agent.get_possible_configurations()
                self.agent.neural_network = self.new_population.models[nueral_net]

                while tetris_game.run:
                    self.agent.landed = tetris_game.landed

                    # update the agent with useful info to find the best move
                    self.agent.update_agent(tetris_game.current_piece)
                    tetris_game.best_move = self.agent.get_best_move(tetris_game.current_piece)

                    tetris_game.game_logic()

                    # make the move
                    tetris_game.make_ai_move()

                    current_fitness += tetris_game.reward_info()

                    self.agent.landed = tetris_game.landed

                    # update the agent with useful info to find the best move
                    self.agent.update_agent(tetris_game.current_piece)

                    if tetris_game.change_piece:
                        tetris_game.change_state()

                    if not tetris_game.run:
                        self.new_population.fitnesses[nueral_net] = current_fitness

                        if current_fitness > self.best_fitness:
                            self.best_fitness = current_fitness
                            self.agent.neural_network.save()

                        print(f'Nueral net fitness: {current_fitness}, Record: {self.best_fitness}')
                        print('==========================================')
                        # reset to a new tetris game, and reset the agent as well
                        break
            self.old_population = self.new_population

    def train(self):
        config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet,
                             neat.DefaultStagnation, 'config-feedfoward.txt')

        p = neat.Population(config)

        p.add_reporter(neat.StdOutReporter(True))
        stats = neat.StatisticsReporter()
        p.add_reporter(stats)

        winner = p.run(self.eval_genomes)

        with open('winner.pkl', 'wb') as output:
            pickle.dump(winner, output, 1)


if __name__ == '__main__':
    trainer = Trainer()

    trainer.eval_genomes()



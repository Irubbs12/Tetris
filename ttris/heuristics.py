import numpy as np

class Heuristics:
    def __init__(self, columns, rows):
        self.width = columns
        self.height = rows
        self.field = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.valids = [(row, col) for row in range(self.height) for col in range(self.width)]

    def update_field(self, field):  # get new field with updated 1s
        self.field = field

    # height of one column
    def column_height(self, column):
        for row in range(self.height):
            if self.field[row][column] == 1:
                return self.height - row
        return 0

    # aggr height
    def aggr_height(self):
        return sum([self.column_height(col) for col in range(self.width)])

    # number of holes in a column
    def column_holes(self, column):
        col_height = self.column_height(column)
        holes = 0

        for row in range(self.height - 1, -1, -1):
            if self.field[row][column] == 0 and (self.height - row) < col_height:
                holes += 1

        return holes

    # number of holes in all columns
    def total_holes(self):
        return sum([self.column_holes(col) for col in range(self.width)])

    # bumpiness of terrain
    def bumpiness(self):
        col_heights = [self.column_height(col) for col in range(self.width)]
        total = 0

        for i in range(len(col_heights) - 2):
            total += abs(col_heights[i] - col_heights[i + 1])

        return total

    # std dev of heights
    def std_heights(self):
        heights = [self.column_height(col) for col in range(self.width)]
        return np.std(heights)

    # number of pits
    def pits(self):
        pits = 0
        for col in range(self.width):
            for row in range(self.height):
                if all([self.field[row][col] == 0]):
                    pits += 1

        return pits

    # number of wells
    def wells(self):
        col_heights = [self.column_height(col) for col in range(self.width)]
        wells = []
        for j in range(len(col_heights)):
            if j == 0:
                depth = col_heights[1] - col_heights[0]
                depth = depth if depth > 0 else 0
                wells.append(depth)
            elif j == len(col_heights) - 1:
                depth = col_heights[-2] - col_heights[-1]
                depth = depth if depth > 0 else 0
                wells.append(depth)
            else:
                depth1 = col_heights[j-1] - col_heights[j]
                depth2 = col_heights[j+1] - col_heights[j]
                depth1 = depth1 if depth1 > 0 else 0
                depth2 = depth2 if depth2 > 0 else 0
                depth = depth1 if depth1 >= depth2 else depth2
                wells.append(depth)

        return wells

    # deepest well
    def deepest_well(self):
        return max(self.wells())

    # lines cleared
    def lines_cleared(self):
        lines = 0

        for row in self.field:
            if 0 not in row:
                lines += 1

        return lines

    def print_stats(self):
        print(f'a. Agg: {self.aggr_height()} \nb. Total Holes: {self.total_holes()} \nc. Bumpiness: {self.bumpiness()} '
              f'\nd. Heights stdDEV:{self.std_heights()} \nPits: {self.pits()}')

    def print_num_grid(self):
        print(' NEW FRAME ....................................')
        for i in self.field:
            print(f'{i} \n')

    def get_heuristics(self):
        return [self.aggr_height(), self.total_holes(), self.bumpiness(), self.std_heights(), self.pits(), self.deepest_well(), self.lines_cleared()]

    def get_reward(self):
        return sum([self.aggr_height()*-2, self.total_holes()*-5, self.bumpiness()*-3, self.std_heights()*-2, self.pits()*2, self.deepest_well()*2])
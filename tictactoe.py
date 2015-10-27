import itertools
import re
import sqlite3
import random


class Board(object):

    def __init__(self, valid_values=None, default_value='_'):
        self.valid_values = valid_values or (lambda x: x in ('_', 'X', 'O'))
        if not self.valid_values(default_value):
            raise ValueError('Invalid value: {}'.format(default_value))
        self._board = [default_value for _ in xrange(9)]

    def copy(self):
        b = Board()
        b._board = self._board[:]
        b.valid_values = self.valid_values
        return b

    def __getitem__(self, key):
        x, y = key
        return self._board[x*3 + y]

    def __setitem__(self, key, value):
        if not self.valid_values(value):
            raise ValueError('Invalid value: {}'.format(repr(value)))
        x, y = key
        self._board[x*3 + y] = value

    def __contains__(self, item):
        return item in self._board

    def __str__(self):
        r = []
        for y in xrange(3):
            for x in xrange(3):
                r.append(self[x, y])
            r.append('\n')
        return ''.join(r)

    @staticmethod
    def row_indexes():
        directions = (
            lambda x, y, d: (x+d, y),
            lambda x, y, d: (x, y+d),
            lambda x, y, d: (x+d, y+d),
            lambda x, y, d: (x+d, y-d))
        rows = []
        for x, y, direction in itertools.product(
                xrange(3), xrange(3), directions):
            rows.append([direction(x, y, d) for d in xrange(3)])
        return [r for r in rows if
                all(x[0] in xrange(3) and x[1] in xrange(3) for x in r)]

    def rows(self):
        r = []
        for rs in self.row_indexes():
            r.append([self[i] for i in rs])
        return r

    def serialize(self):
        return ''.join(self._board)


def winner(board):
    winning_rows = [r for r in board.rows() if
                    r[0] == r[1] == r[2] and r[0] in ('X', 'O')]
    if not winning_rows:
        return None
    return winning_rows[0][0]


class TicTacToe(object):

    def __init__(self, player_1, player_2):
        self.board = Board()
        self.player_1 = player_1
        self.player_2 = player_2

    def play_game(self):
        while True:
            move = self.player_1.move(self.board.copy(), 'X')
            if self.board[move] != '_':
                raise ValueError('{} is an illegal move.'.format(move))
            self.board[move] = 'X'
            if '_' not in self.board or winner(self.board) is not None:
                break
            move = self.player_2.move(self.board.copy(), 'O')
            if self.board[move] != '_':
                raise ValueError('{} is an illegal move.'.format(move))
            self.board[move] = 'O'
            if winner(self.board) is not None:
                break
        self.player_1.game_over(self.board.copy(), 'X')
        self.player_2.game_over(self.board.copy(), 'O')


class HumanPlayer(object):

    def move(self, board, current_player):
        while True:
            print board
            print 'Place an {}:'.format(current_player),
            match = re.match(' *([0-2]) *,? *([0-2]) *', raw_input())
            if not match or (
                    board[int(match.group(1)), int(match.group(2))] != '_'):
                print 'Invalid move.'
            else:
                break
        return int(match.group(1)), int(match.group(2))

    def game_over(self, final_board, player):
        print final_board
        print '{} wins!'.format(winner(final_board))


class ReinforcementLearningPlayer(object):

    def __init__(self):
        self._conn = sqlite3.connect('tictactoe.db')
        self._conn.execute('''
            create table if not exists score
              (board primary key, score)''')
        self._on_policy_moves = []

    def _get_score(self, board, current_player):
        results = tuple(self._conn.execute('''
            select score from score where board = ?''', (board.serialize(),)))
        assert len(results) <= 1
        w = winner(board)
        if w == current_player:
            score = 1
        elif w is not None or '_' not in board:
            score = 0
        else:
            score = .5
        if not results:
            self._conn.execute(
                '''insert into score (board, score) values (?, ?)''',
                (board.serialize(), score))
            self._conn.commit()
            return score
        else:
            return results[0][0]

    def _backup_score(self, current_board, next_board, current_player):
        current_score = self._get_score(current_board, current_player)
        new_score = (
            current_score +
            .2 * (self._get_score(next_board, current_player) - current_score))
        self._conn.execute(
            '''update score set score = ? where board = ?''',
            (new_score, current_board.serialize()))
        self._conn.commit()
        print 'Backup: {} <- {} {}'.format(current_board.serialize(),
                                           next_board.serialize(),
                                           new_score)

    def move(self, board, current_player):
        if self._on_policy_moves and len(self._on_policy_moves[-1]) == 1:
            self._on_policy_moves[-1].append(board)
            self._on_policy_moves[-2].append(board)
        available_moves = [
            (x, y) for x in xrange(3) for y in xrange(3) if
            board[x, y] == '_']
        if random.random() < .1:
            return random.choice(available_moves)
        move_scores = []
        for m in available_moves:
            b = board.copy()
            b[m] = current_player
            move_scores.append((m, self._get_score(b, current_player), b))
        chosen_move = max(move_scores, key=lambda i: i[1])
        self._on_policy_moves.append([chosen_move[2]])
        self._on_policy_moves.append([board])
        return chosen_move[0]

    def game_over(self, final_board, player):
        if self._on_policy_moves and len(self._on_policy_moves[-1]) == 1:
            self._on_policy_moves[-1].append(final_board)
            self._on_policy_moves[-2].append(final_board)
        for earlier_board, later_board in self._on_policy_moves[::-1]:
            self._backup_score(earlier_board, later_board, player)


if __name__ == '__main__':
    TicTacToe(ReinforcementLearningPlayer(), HumanPlayer()).play_game()

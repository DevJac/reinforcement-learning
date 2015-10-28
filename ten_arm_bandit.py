import random


class Bandit(object):

    def __init__(self, arms):
        self.arms = arms
        self._means = [random.randint(-10, 10) for _ in xrange(arms)]

    def _move_means(self):
        def move(n):
            change = random.choice((
                lambda n: n+1,
                lambda n: n-1,
                lambda n: n))
            result = max(-10, min(10, change(n)))
            assert type(result) is int
            return result
        self._means = [move(mean) for mean in self._means]

    def get_arm_value(self, arm):
        self._move_means()
        return random.normalvariate(self._means[arm], 10)


def play_bandit(bandit):
    scores = []
    expected_means = [10 for _ in xrange(bandit.arms)]
    for _ in xrange(1000):
        if random.random() < .01:
            choice = random.randint(0, bandit.arms-1)
        else:
            choice = max(enumerate(expected_means), key=lambda i: i[1])[0]
        v = bandit.get_arm_value(choice)
        scores.append(v)
        expected_means[choice] += .1 * (v - expected_means[choice])
    return scores


if __name__ == '__main__':
    print sum(sum(play_bandit(Bandit(10))) for _ in xrange(1000)) / 1000.

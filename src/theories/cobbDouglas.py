def cobb_douglas(X, Y, alpha, beta, A=1.0):
    """Compute Cobb-Douglas output for two inputs."""
    return A * (X ** alpha) * (Y ** beta)


class CobbDouglas:
    def __init__(self, A, alpha, beta):
        """
        Initialize Cobb-Douglas production function parameters.
        :param A: Total factor productivity
        :param alpha: Output elasticity of input X
        :param beta: Output elasticity of input Y
        """
        self.A = A
        self.alpha = alpha
        self.beta = beta

    def output(self, X, Y):
        """
        Calculate output using Cobb-Douglas production function.
        :param X: Input X (e.g., labor)
        :param Y: Input Y (e.g., capital)
        :return: Output Q
        """
        return self.A * (X ** self.alpha) * (Y ** self.beta)

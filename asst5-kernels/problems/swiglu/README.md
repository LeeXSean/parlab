### SwiGLU
SwiGLU ("Swish-Gated Linear Unit") is an activation function used in modern LLMs, introduced as an improvement over earlier gated linear units.
Usage of SwiGLU can be seen in popular LLMs including and many other recent transformer architectures.

SwiGLU(x, W, V, b, c, beta) = Swish(xW + b) ⊙ (xV + c)
    where Swish(x) = x * sigmoid(beta * x)

Input
* `x`: input tensor of shape [batch_size, seq_len, in_features]
* `W`: weight matrix of shape [in_features, hidden_size]
* `V`: weight matrix of shape [in_features, hidden_size]
* `b`: bias vector of shape [hidden_size,]
* `c`: bias vector of shape [hidden_size,]
* `beta`: scalar value for Swish activation

Output
* Output tensor of shape [batch_size, seq_len, hidden_size]

Reference:
* The original SwiGLU paper is [here](https://arxiv.org/pdf/1710.05941v1).

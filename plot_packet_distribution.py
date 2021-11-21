"""
For the Kalman filter, plot the distribution of our packet and character count due to packetisation
"""
import numpy as np
import random
import matplotlib.pyplot as plt

# %%
plt.figure(dpi=300)
plt.title("Probability mass function of character count for different number of packets")
for N in (1, 2, 3, 5, 10, 20):
    nb_samples = 10000
    x = np.zeros((nb_samples, 1))

    for _ in range(N):
        r = np.random.randint(4, 21, (nb_samples, 1))
        x += r
    
    # x = x / 12 
    # x = (x - N*12) / (4.9*(N**0.5))
    print(x.std() / (N**0.5))

    plt.hist(x, bins=np.arange(x.min(), x.max()+2), density=True, label=f"{N}", histtype=u"step")
    # plt.hist(x, density=True, bins=20, alpha=1.0, label=f"{N}", histtype=u'step')

plt.legend()
plt.ylabel("Probability")
plt.xlabel("Total characters")
plt.grid(True, which='both')
# plt.axvline(N*12, color="r")

# %%
plt.figure(dpi=300)
plt.title("Total number of packets to achieve different number of character counts")
for C in np.array([1,5,10,20,40])*12:
# for C in np.array([5000]):
    nb_samples = 10000
    c = np.zeros((nb_samples, 1))
    x = np.zeros((nb_samples, 1))

    while True:
        r = np.random.randint(4, 21, (nb_samples, 1))
        mask = (c < C).astype(np.int)
        if mask.sum() == 0:
            break
        r = r * mask

        c += r
        x += mask

    N = C / 12 
    # x = (x - N) / (0.41 * (N**0.5))
    print(x.std() / (N**0.5))

    plt.hist(x, density=True, bins=np.arange(np.floor(x.min()), np.ceil(x.max())+2), alpha=1, label=f"{C}", histtype=u"step")
    # plt.hist(x, density=True, bins=np.arange(np.floor(x.min()), np.ceil(x.max())+2), alpha=0.2, label=f"{C}")

plt.legend()
plt.ylabel("Probability")
plt.xlabel("Total packets")
plt.grid()


# %% Show that we can add variances together
N1 = 4
sd1 = 0.41*(N1**0.5)

N2 = 1 
sd2 = 0.41*(N2**0.5)

nb_samples = 10000

x = np.zeros((nb_samples, 1))

for N in (N1, N2):
    sd = 0.41*(N**0.5)
    r = np.random.normal(N, sd, size=(nb_samples, 1))
    x += r

print(x.mean())
print(x.std())
print(sd1**2 + sd2**2, x.std()**2)
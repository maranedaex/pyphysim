#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module containing simulation runners for the several Interference
Alignment algorithms in the algorithms.ia module.
"""

# xxxxxxxxxx Add the parent folder to the python path. xxxxxxxxxxxxxxxxxxxx
import sys
import os
try:
    parent_dir = os.path.split(os.path.abspath(os.path.dirname(__file__)))[0]
    sys.path.append(parent_dir)
except NameError:
    sys.path.append('../')
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# xxxxxxxxxx Import Statements xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
import math
import numpy as np
from matplotlib import pyplot as plt
# import matplotlib as mpl

from pyphysim.util.conversion import dB2Linear, dBm2Linear, linear2dB
from pyphysim.cell import shapes
from pyphysim.comm import pathloss
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


def calc_room_positions_square(side_length, num_cells):
    sqrt_num_cells = int(math.sqrt(num_cells))

    if sqrt_num_cells ** 2 != num_cells:
        raise ValueError("num_cells must be a perfect square number")

    int_positions = np.unravel_index(np.arange(num_cells), (sqrt_num_cells,
                                                            sqrt_num_cells))

    cell_positions = (side_length * (int_positions[1] + 1j *
                                     int_positions[0][::-1] - 0.5-0.5j))

    # Shift the cell positions so that the origin becomes the center of all
    # cells
    shift = side_length * (sqrt_num_cells - 1) // 2
    cell_positions = (cell_positions
                      - shift - 1j * shift
                      + side_length / 2. + 1j * side_length / 2.)

    return cell_positions


def plot_all_rooms(ax, all_rooms):
    """
    Plot all Rectangle shapes in `all_rooms` using the `ax` axis.

    Parameters
    ----------
    ax  : matplotlib axis.
        The axis where the rooms will be plotted.
    all_rooms : shape.Rectangle object
        The room to be plotted.
    """
    for room in all_rooms:
        room.plot(ax)


def calc_num_walls(side_length, room_positions):
    """
    Calculate the number of walls between each room to each other room.

    This is used to calculated the wall losses as well as the indoor
    pathloss.

    Parameters
    ----------
    side_length : float
        The side length of the square cell.
    cell_positions : 1D complex numpy array
        The positions of all cells in grid.

    Returns
    -------
    num_walls : 2D numpy array of ints
        The number of walls from each room to each room.
    """
    num_rooms = room_positions.size

    all_room_positions_diffs = (room_positions.reshape(num_rooms, 1)
                                - 1.0001*room_positions.reshape(1, num_rooms))

    num_walls \
        = np.round(
            np.absolute(np.real(all_room_positions_diffs / side_length)) +
            np.absolute(np.imag(all_room_positions_diffs / side_length))
        ).astype(int)

    return num_walls


def get_cell_users_indexes(cell_index, num_users_per_cell):
    """

    Parameters
    ----------
    cell_index : int
        Index of the desired cell.
    num_users_per_cell : int
        Number of users in each cell.
    """
    return np.arange(0, num_users_per_cell) + cell_index * num_users_per_cell


def prepare_sinr_array_for_color_plot(sinr_array,
                                      num_cells_per_side,
                                      num_discrete_positions_per_cell):
    """

    Parameters
    ----------
    sinr_array : TYPE
    num_cells_per_side : TYPE
    num_discrete_positions_per_cell : TYPE
    """
    dummy = sinr_array
    dummy2 = dummy.reshape(
        [num_cells_per_side,
         num_cells_per_side,
         num_discrete_positions_per_cell,
         num_discrete_positions_per_cell])
    dummy3 = np.swapaxes(dummy2, 1, 2).reshape(
        [num_cells_per_side * num_discrete_positions_per_cell,
         num_cells_per_side * num_discrete_positions_per_cell],
        order='C')
    return dummy3


if __name__ == '__main__':
    # xxxxxxxxxx Simulation Configuration xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    side_length = 10  # 10 meters side length
    single_wall_loss_dB = 5

    # Square of 12 x 12 square cells
    num_cells_per_side = 12
    num_cells = num_cells_per_side ** 2
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # xxxxxxxxxx Discretization of ther possible positions xxxxxxxxxxxxxxxx
    num_discrete_positions_per_cell = 15  # Number of discrete positions
    step = 1. / (num_discrete_positions_per_cell + 1)
    aux = np.linspace(
        -(1. - step), (1. - step), num_discrete_positions_per_cell)
    aux = np.meshgrid(aux, aux, indexing='ij')
    user_relative_positions = aux[0] + 1j * aux[1]
    num_users_per_cell = user_relative_positions.size

    num_discrete_positions_per_dim = (num_discrete_positions_per_cell
                                      *
                                      num_cells_per_side)
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # xxxxxxxxxx Transmit Power and noise xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    Pt = dBm2Linear(30)  # 20 dBm transmit power
    noise_var = 0.0  # dBm2Linear(-116)
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # xxxxxxxxxx Create the rooms xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    cell_positions = calc_room_positions_square(side_length, num_cells)
    all_rooms = [shapes.Rectangle(pos - side_length/2. - side_length*1j/2.,
                                  pos + side_length/2. + side_length*1j/2.)
                 for pos in cell_positions]
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # # xxxxxxxxxx Create the cluster xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    # cluster = cell.Cluster(
    #     cell_radius=side_length, num_cells=num_cells, cell_type='square')
    # # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # xxxxxxxxxx Calculate cell positions and wall losses xxxxxxxxxxxxxxxxx
    # cell_positions = np.array([c.pos for c in cluster])
    num_walls = calc_num_walls(side_length, cell_positions)
    wall_losses_dB = num_walls * single_wall_loss_dB
    wall_losses = dB2Linear(-wall_losses_dB)
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # xxxxxxxxxx Create the path loss object xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    pl_3gpp_obj = pathloss.PathLoss3GPP1()
    pl_free_space_obj = pathloss.PathLossFreeSpace()
    pl_3gpp_obj.handle_small_distances_bool = True
    pl_free_space_obj.handle_small_distances_bool = True
    pl_metis_ps7_obj = pathloss.PathLossMetisPS7()
    pl_metis_ps7_obj.handle_small_distances_bool = True
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # xxxxxxxxxx Add one user in each position of each room xxxxxxxxxxxxxxx
    user_relative_positions2 = user_relative_positions * side_length / 2.
    cell_positions.shape = (12, 12)

    user_positions = (cell_positions[:, :, np.newaxis, np.newaxis] +
                      user_relative_positions2[np.newaxis, np.newaxis, :, :])
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # xxxxxxxxxx Output SINR vector xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    # One output for each case: no pathloss, 3GPP path loss and free space
    # path loss
    sinr_array_pl_nothing = np.zeros(
        [num_cells, num_users_per_cell], dtype=float)
    sinr_array_pl_3gpp = np.zeros(
        [num_cells, num_users_per_cell], dtype=float)
    sinr_array_pl_free_space = np.zeros(
        [num_cells, num_users_per_cell], dtype=float)
    sinr_array_pl_metis_ps7 = np.zeros(
        [num_cells, num_users_per_cell], dtype=float)
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # xxxxxxxxxx Calculate the distance and path losses xxxxxxxxxxxxxxx
    dists_m = np.abs(user_positions.flatten()[:, np.newaxis] -
                     cell_positions.flatten()[np.newaxis, :])

    # 3GPP and Free Space path loss classes require distance values to be
    # in Km. Therefore, we divide the distance in meters by 1000.
    pl_3gpp = pl_3gpp_obj.calc_path_loss(dists_m/1000.)
    pl_free_space = pl_free_space_obj.calc_path_loss(dists_m/1000.)
    pl_nothing = np.ones([num_cells * num_users_per_cell, num_cells],
                         dtype=float)

    # We need to know the number of walls the signal must pass to reach the
    # receiver to calculate the path loss for the METIS PS7 model.
    num_walls_extended = np.repeat(num_walls, 15*15, axis=0)

    # The METIS PS7 path loss model require distance values in meters,
    # while the others are in Kms.
    pl_metis_ps7 = pl_metis_ps7_obj.calc_path_loss(
        dists_m,
        num_walls=num_walls_extended)
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    for cell_idx in range(num_cells):
        # Index of the users in the current cell
        users_idx = get_cell_users_indexes(cell_idx, num_users_per_cell)

        # Mask to get path loss of all transmitters ...
        mask = np.ones(num_cells, dtype=bool)
        # ... except the desired transmitter
        mask[cell_idx] = 0

        # xxxxxxxxxx Case without pathloss xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        pl = pl_nothing

        # Get the desired power of the users in the cell
        desired_power = Pt * pl[users_idx, cell_idx]

        # Calculate the sum of all interference powers
        undesired_power = np.sum(
            Pt * pl[users_idx][:, mask] * wall_losses[cell_idx, mask],
            axis=-1)

        # Calculate the SINR of the user
        sinr_users_in_current_cell = (desired_power /
                                      (undesired_power + noise_var))
        sinr_array_pl_nothing[cell_idx, :] = sinr_users_in_current_cell
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxxxxxxx Case with 3GPP pathloss xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        pl = pl_3gpp

        # Get the desired power of the users in the cell
        desired_power = Pt * pl[users_idx, cell_idx]

        # Calculate the sum of all interference powers
        undesired_power = np.sum(
            Pt * pl[users_idx][:, mask] * wall_losses[cell_idx, mask],
            axis=-1)

        # Calculate the SINR of the user
        sinr_users_in_current_cell = (desired_power /
                                      (undesired_power + noise_var))
        sinr_array_pl_3gpp[cell_idx, :] = sinr_users_in_current_cell
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxxxxxxx Case with Free Space path loss xxxxxxxxxxxxxxxxxxxxxxx
        pl = pl_free_space

        # Get the desired power of the users in the cell
        desired_power = Pt * pl[users_idx, cell_idx]

        # Calculate the sum of all interference powers
        undesired_power = np.sum(
            Pt * pl[users_idx][:, mask] * wall_losses[cell_idx, mask],
            axis=-1)

        # Calculate the SINR of the user
        sinr_users_in_current_cell = (desired_power /
                                      (undesired_power + noise_var))
        sinr_array_pl_free_space[cell_idx, :] = sinr_users_in_current_cell
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxxxxxxx Case with METIS PS7 path loss xxxxxxxxxxxxxxxxxxxxxxxx
        pl = pl_metis_ps7

        # Get the desired power of the users in the cell
        desired_power = Pt * pl[users_idx, cell_idx]

        # Calculate the sum of all interference powers
        undesired_power = np.sum(
            Pt * pl[users_idx][:, mask] * wall_losses[cell_idx, mask],
            axis=-1)

        # Calculate the SINR of the user
        sinr_users_in_current_cell = (desired_power /
                                      (undesired_power + noise_var))
        sinr_array_pl_metis_ps7[cell_idx, :] = sinr_users_in_current_cell
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # xxxxxxxxxx Convert values to dB xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    sinr_array_pl_nothing_dB = linear2dB(sinr_array_pl_nothing)
    sinr_array_pl_3gpp_dB = linear2dB(sinr_array_pl_3gpp)
    sinr_array_pl_free_space_dB = linear2dB(sinr_array_pl_free_space)
    sinr_array_pl_metis_ps7_dB = linear2dB(sinr_array_pl_metis_ps7)
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    print ("Min/Mean/Max SINR value (no PL):"
           "\n    {0}\n    {1}\n    {2}").format(
               sinr_array_pl_nothing_dB.min(),
               sinr_array_pl_nothing_dB.mean(),
               sinr_array_pl_nothing_dB.max())
    print ("Min/Mean/Max SINR value (3GPP):"
           "\n    {0}\n    {1}\n    {2}").format(
               sinr_array_pl_3gpp_dB.min(),
               sinr_array_pl_3gpp_dB.mean(),
               sinr_array_pl_3gpp_dB.max())
    print ("Min/Mean/Max SINR value (Free Space):"
           "\n    {0}\n    {1}\n    {2}").format(
               sinr_array_pl_free_space_dB.min(),
               sinr_array_pl_free_space_dB.mean(),
               sinr_array_pl_free_space_dB.max())
    print ("Min/Mean/Max SINR value (METIS PS7):"
           "\n    {0}\n    {1}\n    {2}").format(
               sinr_array_pl_free_space_dB.min(),
               sinr_array_pl_metis_ps7_dB.mean(),
               sinr_array_pl_free_space_dB.max())

    # xxxxxxxxxx Prepare data to be plotted xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    sinr_array_pl_nothing_dB2 = prepare_sinr_array_for_color_plot(
        sinr_array_pl_nothing_dB,
        num_cells_per_side,
        num_discrete_positions_per_cell)
    sinr_array_pl_3gpp_dB2 = prepare_sinr_array_for_color_plot(
        sinr_array_pl_3gpp_dB,
        num_cells_per_side,
        num_discrete_positions_per_cell)
    sinr_array_pl_free_space_dB2 = prepare_sinr_array_for_color_plot(
        sinr_array_pl_free_space_dB,
        num_cells_per_side,
        num_discrete_positions_per_cell)
    sinr_array_pl_metis_ps7_dB2 = prepare_sinr_array_for_color_plot(
        sinr_array_pl_metis_ps7_dB,
        num_cells_per_side,
        num_discrete_positions_per_cell)
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # xxxxxxxxxx Plot each case xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    # No path loss
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    im1 = ax1.imshow(sinr_array_pl_nothing_dB2,
                     interpolation='nearest', vmax=-1.5, vmin=-5)
    ax1.set_title('No Path Loss')
    fig1.colorbar(im1)

    # 3GPP path loss
    fig2, ax2 = plt.subplots(figsize=(8, 6))
    im2 = ax2.imshow(sinr_array_pl_3gpp_dB2,
                     interpolation='nearest', vmax=30, vmin=-2.5)
    ax2.set_title('3GPP Path Loss')
    fig2.colorbar(im2)

    # Free Space path loss
    fig3, ax3 = plt.subplots(figsize=(8, 6))
    im3 = ax3.imshow(sinr_array_pl_free_space_dB2,
                     interpolation='nearest', vmax=30, vmin=-2.5)
    ax3.set_title('Free Space Path Loss')
    fig3.colorbar(im3)

    # METIS PS7 path loss
    fig4, ax4 = plt.subplots(figsize=(8, 6))
    im4 = ax4.imshow(sinr_array_pl_metis_ps7_dB2,
                     interpolation='nearest', vmax=30, vmin=-2.5)
    ax4.set_title('METIS PS7 Path Loss')
    fig4.colorbar(im4)

    plt.show()
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

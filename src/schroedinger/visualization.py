"""Animations with bounded colour-scale sampling and playback controls."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, Slider


def _density(simulation, frame):
    if hasattr(simulation, "density"):
        return simulation.density(frame)
    return np.abs(simulation[frame])**2


def _time(simulation, frame, config):
    return simulation.times[frame] if hasattr(simulation, "times") else (
        frame * config.simulation_params.save_every * config.initial_values.dt)


def _norm(simulation, frame, config):
    return simulation.norms[frame] if hasattr(simulation, "norms") else (
        _density(simulation, frame).sum() * config.cell_volume)


def _colour_limit(simulation, percentile, skip_fraction):
    if not 0 < percentile <= 100 or not 0 <= skip_fraction < 1:
        raise ValueError("Invalid colour-scale percentile or skip fraction")
    skip = min(len(simulation)-1, int(len(simulation)*skip_fraction))
    selected = np.linspace(skip, len(simulation)-1, min(24, len(simulation)-skip), dtype=int)
    size = np.size(simulation[0])
    stride = max(1, int(np.ceil(size*len(selected)/200000)))
    values = np.concatenate([_density(simulation, int(i)).ravel()[::stride] for i in selected])
    vmax = float(np.percentile(values, percentile))
    if vmax <= 0:
        vmax = float(max(np.max(_density(simulation, i)) for i in range(len(simulation))))
    return max(vmax, np.finfo(float).tiny)


def _add_controls(fig, animation, update, count):
    if count < 2:
        return None
    playing = True
    button = Button(fig.add_axes([0.12, 0.035, 0.12, 0.04]), "Pause")
    restart = Button(fig.add_axes([0.26, 0.035, 0.12, 0.04]), "Restart")
    slider = Slider(fig.add_axes([0.48, 0.045, 0.36, 0.02]), "Frame", 0, count-1,
                    valinit=0, valstep=1, valfmt="%0.0f")

    def toggle(_):
        nonlocal playing
        playing = not playing
        animation.resume() if playing else animation.pause()
        button.label.set_text("Pause" if playing else "Play")
        fig.canvas.draw_idle()

    def reset(_):
        nonlocal playing
        animation.frame_seq = animation.new_frame_seq()
        update(0)
        playing = True
        button.label.set_text("Pause")
        animation.resume()
        fig.canvas.draw_idle()

    def seek(value):
        nonlocal playing
        animation.pause()
        playing = False
        button.label.set_text("Play")
        frame = int(value)
        animation.frame_seq = iter(range(frame+1, count))
        update(frame)
        fig.canvas.draw_idle()

    button.on_clicked(toggle)
    restart.on_clicked(reset)
    slider.on_changed(seek)
    animation._schroedinger_controls = (button, restart, slider)

    def sync(frame):
        slider.eventson = False
        slider.set_val(frame)
        slider.eventson = True
    return sync


def animate(simulation, config, potential=None, barrier_mask=None, interval=40,
            vmax_percentile=99.5, vmax_skip_initial_frac=0.25, show=True):
    if not len(simulation):
        raise ValueError("Animation needs at least one frame")
    iv = config.initial_values
    fig, ax = plt.subplots(figsize=(10, 5.8))
    fig.canvas.manager.set_window_title(f"Akademie Olympia - Schrodinger {config.dimension}D")
    fig.subplots_adjust(bottom=0.19)
    controls = None

    if config.dimension == 1:
        x = iv.x_grid
        density_only = getattr(simulation, "is_density", False)
        density_line, = ax.plot(x, _density(simulation, 0), label=r"$|\psi|^2$")
        lines = [density_line]
        if not density_only:
            real_line, = ax.plot(x, np.real(simulation[0]), lw=1, label=r"Re $\psi$")
            imag_line, = ax.plot(x, np.imag(simulation[0]), lw=1, label=r"Im $\psi$")
            lines.extend([real_line, imag_line])
        scale = max(max(float(np.max(np.abs(frame))) for frame in simulation),
                    max(float(np.max(_density(simulation, i))) for i in range(len(simulation))), 0.1)
        ax.set_ylim(-1.15*scale, 1.3*scale)
        ax.set_xlim(x[0], x[-1])
        ax.set_xlabel("x")
        ax.set_ylabel("Wave function / probability density")
        if potential is not None:
            right = ax.twinx()
            right.plot(x, potential, color="orange", alpha=0.4, label="V")
            right.set_ylabel("Potential V", color="darkorange")
        ax.legend(loc="upper left")

        def update(frame):
            lines[0].set_ydata(_density(simulation, frame))
            if not density_only:
                lines[1].set_ydata(np.real(simulation[frame]))
                lines[2].set_ydata(np.imag(simulation[frame]))
            ax.set_title(f"t = {_time(simulation, frame, config):.4f}    "
                         f"P = {_norm(simulation, frame, config):.6f}")
            if controls is not None:
                controls(frame)
            return tuple(lines)
    else:
        extent = (iv.x_min-iv.dx/2, iv.x_max-iv.dx/2,
                  iv.y_min-iv.dy/2, iv.y_max-iv.dy/2)
        im = ax.imshow(_density(simulation, 0), extent=extent, origin="lower",
                       cmap="inferno", vmin=0,
                       vmax=_colour_limit(simulation, vmax_percentile, vmax_skip_initial_frac),
                       interpolation="bilinear", aspect="equal")
        x, y = np.meshgrid(iv.x_grid, iv.y_grid, indexing="xy")
        if barrier_mask is not None and np.any(barrier_mask) and not np.all(barrier_mask):
            ax.contour(x, y, barrier_mask.astype(float), levels=[0.5], colors="white", linewidths=0.8)
        elif potential is not None and np.ptp(potential) > 0:
            ax.contour(x, y, potential, levels=[float((np.max(potential)+np.min(potential))/2)],
                       colors="white", linewidths=0.8)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        fig.colorbar(im, ax=ax, label=r"$|\psi|^2$")

        def update(frame):
            im.set_data(_density(simulation, frame))
            ax.set_title(r"$|\psi(x,y,t)|^2$" +
                         f"    t = {_time(simulation, frame, config):.3f}    "
                         f"P = {_norm(simulation, frame, config):.5f}")
            if controls is not None:
                controls(frame)
            return im,

    animation = FuncAnimation(fig, update, frames=len(simulation), interval=interval,
                              blit=False, cache_frame_data=False)
    controls = _add_controls(fig, animation, update, len(simulation))
    update(0)
    if show:
        plt.show()
    return animation

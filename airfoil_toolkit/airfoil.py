import numpy as np
import aerosandbox as asb
from typing import Union, List
from pathlib import Path
from airfoil_toolkit.aux import eng_string
from aerosandbox.geometry.airfoil.airfoil_families import (
    get_NACA_coordinates,
    get_UIUC_coordinates,
    get_file_coordinates,
)


class Airfoil:
    def __init__(
        self,
        name: str = "Untitled",
        coordinates: str = None,
    ):
        """
        Initializes an Airfoil object with a given name and optional coordinates path.

        Attempts to retrieve airfoil coordinates based on the provided name from
        NACA or UIUC databases if no coordinates path is specified. If a path is
        provided, it assumes the path points to a .dat file containing the coordinates.

        Args:
            name (str): The name of the airfoil. Defaults to "Untitled".
            coordinates (Union[str, None]): Optional path to a .dat file containing
                airfoil coordinates. Defaults to None.

        Raises:
            UserWarning: If no coordinates could be assigned to the airfoil.
        """
        self.name = name
        self.coordinates = coordinates

        if coordinates is None:
            try:  # See if it's a NACA airfoil
                self.coordinates = get_NACA_coordinates(name=self.name)
            except (ValueError, NotImplementedError):
                try:  # See if it's in the UIUC airfoil database
                    self.coordinates = get_UIUC_coordinates(name=self.name)
                except FileNotFoundError:
                    pass
        else:
            # If coordinates is a string, assume it's a filepath to a .dat file
            self.coordinates = get_file_coordinates(coordinates)

        if self.coordinates is None:
            raise Exception(
                f"Airfoil {self.name} had no coordinates assigned, and could not parse the `coordinates` input!",
            )
        else:
            self.x = self.coordinates[:, 0]
            self.y = self.coordinates[:, 1]

    def __repr__(self) -> str:
        return f"Airfoil {self.name}"

    def draw(
        self, draw_mcl=False, draw_markers=True, backend="matplotlib", show=True
    ) -> None:
        """
        Draw the airfoil object.

        Args:
            draw_mcl: Should we draw the mean camber line (MCL)? [boolean]

            backend: Which backend should we use? "plotly" or "matplotlib"

            show: Should we show the plot? [boolean]

        Returns: None
        """
        x = np.reshape(np.array(self.x), -1)
        y = np.reshape(np.array(self.y), -1)
        # if draw_mcl:
        #     x_mcl = np.linspace(np.min(x), np.max(x), len(x))
        #     y_mcl = self.local_camber(x_mcl)

        if backend == "matplotlib":
            import matplotlib.pyplot as plt
            import aerosandbox.tools.pretty_plots as p

            color = "#280887"
            plt.plot(x, y, ".-" if draw_markers else "-", zorder=11, color=color)
            plt.fill(x, y, zorder=10, color=color, alpha=0.2)
            # if draw_mcl:
            #     plt.plot(x_mcl, y_mcl, "-", zorder=4, color=color, alpha=0.4)
            plt.axis("equal")
            if show:
                p.show_plot(
                    title=f"{self.name} Airfoil",
                    xlabel=r"$x/c$",
                    ylabel=r"$y/c$",
                )

        elif backend == "plotly":
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    mode="lines+markers" if draw_markers else "lines",
                    name="Airfoil",
                    fill="toself",
                    line=dict(color="blue"),
                ),
            )
            # if draw_mcl:
            #     fig.add_trace(
            #         go.Scatter(
            #             x=x_mcl,
            #             y=y_mcl,
            #             mode="lines",
            #             name="Mean Camber Line (MCL)",
            #             line=dict(color="navy"),
            #         )
            #     )
            fig.update_layout(
                xaxis_title="x/c",
                yaxis_title="y/c",
                yaxis=dict(scaleanchor="x", scaleratio=1),
                title=f"{self.name} Airfoil",
            )
            if show:
                fig.show()
            else:
                return fig

    def write_dat(
        self,
        filepath: Union[Path, str] = None,
        include_name: bool = True,
    ) -> str:
        """
        Writes a .dat file corresponding to this airfoil to a filepath.

        Args:
            filepath: filepath (including the filename and .dat extension) [string]
                If None, this function returns the .dat file as a string.

            include_name: Should the name be included in the .dat file? (In a standard *.dat file, it usually is.)

        Returns: None

        """
        contents = []

        if include_name:
            contents += [self.name]

        contents += ["%f %f" % tuple(coordinate) for coordinate in self.coordinates]

        string = "\n".join(contents)

        if filepath is not None:
            with open(filepath, "w+") as f:
                f.write(string)

        return string

    def generate_polars_xfoil(
        self,
        alpha_i: float = 0.0,
        alpha_f: float = 10.0,
        alpha_step: float = 0.25,
        Res: np.ndarray = np.geomspace(1e4, 1e6, 12),
        n_iter: int = 100,
        min_points_to_converged: int = 20,
        working_directory: str = None,
    ) -> dict:
        """
        Generates polar data for the airfoil using XFOIL over a specified range of angles of attack.

        This method utilizes the `run_xfoil` function to perform simulations and retrieve polar data,
        which includes lift, drag, and moment coefficients for the airfoil at various angles of attack.

        Args:
            alpha_i (float): Initial angle of attack in degrees. Defaults to 0.0.
            alpha_f (float): Final angle of attack in degrees. Defaults to 10.0.
            alpha_step (float): Step size for the angle of attack in degrees. Defaults to 0.25.
            Re (int): Reynolds number for the simulation. Defaults to 1000000.
            n_iter (int): Maximum number of iterations for convergence. Defaults to 100.
            min_points_to_converged (int): Minimum number of points required for convergence. Defaults to 20.
            working_directory (str, optional): Directory to use for temporary files. Defaults to None.

        Returns:
            dict: Dictionary containing the polar data from the XFOIL simulation.
        """

        from airfoil_toolkit.xfoil import run_xfoil
        from tqdm import tqdm

        # Get a list of dicts, where each dict is the result of an XFoil run at a particular Re.
        run_datas = [
            run_xfoil(self, alpha_i, alpha_f, alpha_step, Re, n_iter, working_directory)
            for Re in tqdm(
                Res,
                desc=f"Running XFoil to generate polars for Airfoil '{self.name}':",
            )
        ]

        self.polars = run_datas
        self.Res = Res

        return self.polars

        # """Descarta os perfis que não convergirem"""
        # try:
        #     alpha = polar_data[:, 0]
        #     if len(alpha) < min_points_to_converged:
        #         self.converged = False
        #     else:
        #         Cl = polar_data[:, 1]
        #         Cd = polar_data[:, 2]
        #         self.converged = (
        #             True  # Estado que determina se o perfil convergiu na análise
        #         )

    def plot_polars(
        self,
    ) -> None:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(2, 2, figsize=(9, 8))
        for data in self.polars:
            ax[0, 0].plot(data["alpha"], data["CL"])
            ax[0, 0].set(
                xlabel=r"Angle of Attack $\alpha$ [deg]",
                ylabel="Lift Coefficient $C_L$",
            )

            ax[0, 1].plot(data["alpha"], data["CD"])
            ax[0, 1].set(
                xlabel=r"Angle of Attack $\alpha$ [deg]",
                ylabel="Drag Coefficient $C_D$",
            )

            ax[1, 0].plot(data["alpha"], data["CM"])
            ax[1, 0].set(
                xlabel=r"Angle of Attack $\alpha$ [deg]",
                ylabel="Moment Coefficient $C_m$",
            )

            ax[1, 1].plot(data["CL"], data["CD"])
            ax[1, 1].set(
                xlabel=r"Angle of Attack $\alpha$ [deg]",
                ylabel=r"Lift-to-Drag Ratio $C_L/C_D$",
            )

        plt.sca(ax[0, 0])
        plt.legend(
            title="Reynolds Number",
            labels=[eng_string(Re) for Re in self.Res],
            ncol=2,
            # Note: `ncol` is old syntax; preserves backwards-compatibility with matplotlib 3.5.x.
            # New matplotlib versions use `ncols` instead.
            fontsize=8,
            loc="lower right",
        )

        # for i, Re in enumerate(Res):
        #     kwargs = dict(alpha=alphas, Re=Re, mach=mach)

        #     plt.sca(ax[0, 0])
        #     plt.plot(self.polars["alphas"], self.CL_function(**kwargs), color=Re_colors[i], alpha=0.7)

        #     plt.sca(ax[0, 1])
        #     plt.plot(alphas, self.CD_function(**kwargs), color=Re_colors[i], alpha=0.7)

        #     plt.sca(ax[1, 0])
        #     plt.plot(alphas, self.CM_function(**kwargs), color=Re_colors[i], alpha=0.7)

        #     plt.sca(ax[1, 1])
        #     plt.plot(
        #         alphas,
        #         self.CL_function(**kwargs) / self.CD_function(**kwargs),
        #         color=Re_colors[i],
        #         alpha=0.7,
        #     )

        # from aerosandbox.tools.string_formatting import eng_string

        # plt.sca(ax[0, 0])
        # plt.legend(
        #     title="Reynolds Number",
        #     labels=[eng_string(Re) for Re in Res],
        #     ncol=2,
        #     # Note: `ncol` is old syntax; preserves backwards-compatibility with matplotlib 3.5.x.
        #     # New matplotlib versions use `ncols` instead.
        #     fontsize=8,
        #     loc="lower right",
        # )


if __name__ == "__main__":
    pass

import discord
from discord import app_commands
from discord.ext import commands
import random

# Custom Button representing a Minesweeper cell.
class MinesweeperButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        # Use a placeholder emoji initially.
        super().__init__(label="⬛", style=discord.ButtonStyle.primary)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: MinesweeperView = self.view  # type: ignore

        # Only the original player can interact with the game.
        if interaction.user.id != view.owner_id:
            await interaction.response.send_message("Shush! Play your own game!", ephemeral=True)
            return

        if view.game_over:
            return  # Ignore interactions if the game is already over.

        # If the selected cell is a mine.
        if view.board[self.x][self.y] == -1:
            self.style = discord.ButtonStyle.danger
            self.label = "💣"
            view.game_over = True
            # Reveal all mines and disable all buttons.
            for item in view.children:
                if isinstance(item, MinesweeperButton):
                    item.disabled = True
                    if view.board[item.x][item.y] == -1:
                        item.label = "💣"
            await interaction.response.edit_message(view=view)
            await interaction.followup.send("Boom! You hit a mine. Game over.")
        else:
            # Count adjacent mines.
            count = view.count_adjacent_mines(self.x, self.y)
            # Show the count if greater than 0; otherwise, leave it blank.
            self.label = str(count) if count > 0 else "\u200b"
            self.disabled = True
            view.revealed += 1
            await interaction.response.edit_message(view=view)
            # Check win condition: all safe cells are revealed.
            if view.revealed == view.safe_cells:
                view.game_over = True
                for item in view.children:
                    item.disabled = True
                await interaction.followup.send("Congratulations! You cleared all safe cells and won!")

# Custom View that manages the game state and buttons.
class MinesweeperView(discord.ui.View):
    def __init__(self, rows: int, columns: int, mines: int, owner_id: int, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.rows = rows
        self.columns = columns
        self.mines = mines
        self.owner_id = owner_id  # Store the ID of the player who started the game.
        self.board = self.generate_board()
        self.game_over = False
        self.revealed = 0
        # Calculate the number of safe cells.
        self.safe_cells = rows * columns - mines

        # Create a grid of buttons.
        for i in range(rows):
            for j in range(columns):
                button = MinesweeperButton(i, j)
                button.row = i  # Set the button's row explicitly
                self.add_item(button)


    def generate_board(self):
        # Create an empty board.
        board = [[0 for _ in range(self.columns)] for _ in range(self.rows)]
        # Randomly choose positions for mines.
        positions = [(i, j) for i in range(self.rows) for j in range(self.columns)]
        mine_positions = random.sample(positions, self.mines)
        for (i, j) in mine_positions:
            board[i][j] = -1  # -1 indicates a mine.
        return board

    def count_adjacent_mines(self, x: int, y: int) -> int:
        count = 0
        # Iterate over the 8 adjacent cells.
        for i in range(max(0, x - 1), min(self.rows, x + 2)):
            for j in range(max(0, y - 1), min(self.columns, y + 2)):
                if i == x and j == y:
                    continue
                if self.board[i][j] == -1:
                    count += 1
        return count

# Cog that defines the Minesweeper slash command.
class Minesweeper(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="minesweeper", description="Play a game of Minesweeper!")
    @app_commands.describe(
        rows="Number of rows (min 2, max 5)",
        columns="Number of columns (min 2, max 5)",
        mines="Number of mines (default ~20% of cells)"
    )
    async def minesweeper(self, interaction: discord.Interaction, rows: int = 5, columns: int = 5, mines: int = None):
        # Validate grid dimensions.
        min_grid = 2
        max_grid = 5
        if rows < min_grid or rows > max_grid or columns < min_grid or columns > max_grid:
            await interaction.response.send_message(f"Rows and columns must be between {min_grid} and {max_grid}.", ephemeral=True)
            return

        total_cells = rows * columns
        default_mines = max(1, total_cells // 5)  # Roughly 20% mines by default.
        if mines is None:
            mines = default_mines

        # Cap mines to ensure playability.
        mines_cap = total_cells // 2
        if mines < 1 or mines > mines_cap:
            await interaction.response.send_message(f"Mines must be between 1 and {mines_cap}.", ephemeral=True)
            return

        # Pass the command invoker's ID to the view.
        view = MinesweeperView(rows, columns, mines, owner_id=interaction.user.id)
        await interaction.response.send_message(
            f"Here's your Minesweeper board!\nRows: {rows}, Columns: {columns}, Mines: {mines}",
            view=view
        )

# Setup function to add the cog to your bot.
async def setup(bot: commands.Bot):
    await bot.add_cog(Minesweeper(bot))
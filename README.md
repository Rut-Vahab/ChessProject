# README - KungFu Chess Project

## Overview

This project is a real-time chess-like game called **KungFu Chess**. It supports multiple clients connecting to a central game server, move validation, pawn promotion, piece capture, score tracking, and victory conditions. The project also includes animations, sound effects, and comprehensive unit tests.

## Features

* **Server-Client Architecture** using WebSockets.
* **Real-time multiplayer gameplay**.
* **Move validation** for all pieces (basic for some, full rules for knights initially).
* **Pawn promotion** automatic handling.
* **Piece capture** with score updates.
* **Victory detection** when a king is captured.
* **Animations and sound effects** integrated.
* **Unit tests** covering core game logic and move execution.
* **Flexible for extensions**: new pieces, custom rules, or UI enhancements.

## Project Structure

```
KungFuChess/
│
├─ server/
│  ├─ GameState.py
│  ├─ GameServer.py
|    tests/
│  ├─ test_game_state.py
│  ├─ test_moves.py
│  └─ ...
│  └─ ...
│
├─ client/
│  ├─ GameClient.py
│  ├─ Board.py
│  ├─ Img.py
|  ├─   board.csv
|  ├─ board.png
|    PIECES/
|     ├─ NW/moves.txt
|     ├─ NB/moves.txt
|      └─ ...
|   tests/
│  ├─ test_game_state.py
│  ├─ test_moves.py
│  └─ ...
│  
├─ configs/
│  └─ ...
│
|
└─ README.md
```

## Server Setup

1. **Install dependencies:**

```bash
pip install websockets
```

2. **Run the server:**

```bash
python server/GameServer.py
```

3. **Server defaults:**

   * Host: `0.0.0.0`
   * Port: `8765` (can override using `PORT` environment variable)

## Client Setup

1. **Install dependencies:**

```bash
pip install websockets
```

2. **Prepare board and pieces:**

   * `board.png` for visuals
   * `PIECES/` folder containing piece directories and `moves.txt`
   * `board.csv` for initial placement if needed

3. **Run the client:**

```bash
python client/GameClient.py
```

4. **Client behavior:**

   * Connects to the server
   * Receives color assignment (`white` or `black`)
   * Syncs full game state
   * Sends moves to server
   * Updates local board with server-confirmed moves

## Gameplay Rules

* No turn enforcement (KungFu Chess allows any player to move at any time).
* **Pawn promotion:** automatically promoted to queen on last row.
* **Move validation:** currently enforced strictly for knights; other pieces may have basic rules.
* **Capture events:** update score and trigger victory if king is captured.

## Event System

* `EventManager` publishes events:

  * `move_made`
  * `piece_captured`
  * `game_start`
* `MoveHistory`, `ScoreBoard`, and `VictoryManager` subscribe to relevant events.

## Running Unit Tests

1. Navigate to the `tests/` directory.
2. Run all tests:

```bash
pytest
```

Tests cover:

* Move validation
* Pawn promotion
* Capture detection
* Score updates
* Victory conditions

## Extending the Project

* Add new piece types by creating a folder in `PIECES/` with `moves.txt`.
* Update move validation logic in `GameState.py`.
* Enhance the client with GUI improvements or sound effects.

## Notes

* The project has been **thoroughly tested** for move execution, capture, promotion, and victory conditions.
* Designed for **high maintainability** and **easy extension**.
* All networking is handled via WebSockets, allowing deployment on servers such as **Railway** or local environments.

---

End of README

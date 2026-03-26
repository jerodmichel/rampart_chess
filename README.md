# Rampart ♟️

[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0) 
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/) 
[![Pygame](https://img.shields.io/badge/Pygame-2.5+-red.svg)](https://www.pygame.org)

A strategic hybrid of chess and cardplay where players battle across a rampart barrier using tactical movement and card-based casting.

    ██████╗░░█████╗░███╗░░░███╗██████╗░░█████╗░██████╗░████████╗
    ██╔══██╗██╔══██╗████╗░████║██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝
    ██████╔╝███████║██╔████╔██║██████╔╝███████║██████╔╝░░░██║░░░
    ██╔══██╗██╔══██║██║╚██╔╝██║██╔═══╝░██╔══██║██╔══██╗░░░██║░░░
    ██║░░██║██║░░██║██║░╚═╝░██║██║░░░░░██║░░██║██║░░██║░░░██║░░░
    ╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░░░░╚═╝╚═╝░░░░░╚═╝░░╚═╝╚═╝░░╚═╝░░░╚═╝░░░

<p>
  <img src="screenshots/rampart_bg.png" width="500">
</p>

## 🎮 Download & Play (Windows)
No installation required! To play immediately:
1. Go to the **[Releases](../../releases)** tab on the right side of this page.
2. Download the latest `Rampart_Windows_v1.0.zip`.
3. Extract the folder to your PC and double-click **`Rampart.exe`** (the launcher) to play!

## Video Demo

Watch full games of Rampart:

<table style="width:100%">
  <tr>
    <td align="center"><b>Full Gameplay (Client)</b></td>
    <td align="center"><b>Full Gameplay (AI)</b></td>
  </tr>
  <tr>
    <td align="center">
      <a href="https://www.youtube.com/watch?v=TWDltWxu2pY">
        <img src="https://img.youtube.com/vi/TWDltWxu2pY/0.jpg" width="300">
      </a>
    </td>
    <td align="center">
      <a href="https://www.youtube.com/watch?v=Klb_kVEQBv4">
        <img src="https://img.youtube.com/vi/Klb_kVEQBv4/0.jpg" width="300">
      </a>
    </td>
  </tr>
</table>


*Click the image above to watch the full gameplay video on YouTube*

## Screenshots

| Multiplayer | Cast Move | AI Mode |
|----------|--------------|-------------|
| <img src="screenshots/screen2.png" width="300"> | <img src="screenshots/screen1.png" width="300"> | <img src="screenshots/screen4.png" width="300"> |
| <img src="screenshots/screen3.png" width="300"> | <img src="screenshots/screen5.png" width="300"> | <img src="screenshots/screen6.png" width="300"> |

## Features
| Category                 | Highlights                                                                 |
|--------------------------|----------------------------------------------------------------------------|
| **Hybrid Gameplay** | Chess pieces + cardplay • Casting with card combinations                   |
| **Single Player AI** | Custom Negamax AI engine for local offline play                            |
| **Realtime Multiplayer** | Firebase-powered battles • 4-digit PIN to join game                        |
| **Customization** | Switchable themes (`T`) • Alternate piece styles (`Y`)                     |
| **Tactical Depth** | Lightning animations • Graveyard resurrection mechanics                    |

## Official Rules
[![Rulebook PDF](https://img.shields.io/badge/Download-Rulebook-blue)](https://osf.io/a3cfz)  
Complete strategy guide including card combinations and special moves.

---

## Build from Source (For Developers)
If you want to view the code, run from the Python source, or contribute:

    # Clone using your actual GitHub username
    git clone https://github.com/jerodmichel/rampart.git
    cd rampart
    
    # Install Python dependencies
    pip install -r requirements.txt
    
    # Run the launcher
    python launcher.py

## Controls
| Key       | Action                          | Mode           |
|-----------|---------------------------------|----------------|
| `H` / `J` | Host / Join game                | Main menu      | 
| `F`       | Flip board perspective          | Global         |
| `T` / `Y` | Switch theme / piece style      | Global         |
| `S` / `L` | Save / Load Game                | Host Only      |
| `<-` / `->`| Step back/forward in history   | Global         |
| `R`       | Request rematch                 | Multiplayer    |
| `C`       | Open chat                       | Multiplayer    |

## Architecture
    mermaid
    flowchart LR
      A[launcher.py] --> B[Game Loop]
      B --> C[Pygame Rendering]
      B --> D[Firebase Sync]
      B --> E[Board Logic]
      B --> F[Negamax AI Engine]

## Roadmap
- [x] Multiplayer core (v1.0)
- [x] Card casting system (v1.0)
- [x] AI opponent (v1.1)
- [x] Native Linux Release (v1.1)
- [ ] Mobile touch support (v1.2)
- [ ] Tournament mode (v1.3)

## License
    Rampart - A strategic hybrid of chess and cardplay
    Copyright (C) 2024-2026 Jerod Michel
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

## Credits
Developed by **Jerod Michel** using:
- <img src="https://www.pygame.org/favicon.ico" width=16> Pygame
- <img src="https://www.gnu.org/graphics/gplv3-88x31.png" width=16> GPLv3
- <img src="https://www.python.org/static/favicon.ico" width=16> Python 3.8+

**Supporting developers:** Yucheng Gao, Mac McMorran

**Splash art/other art:** Leland Struebig/Billy Hill

**Additional Code Support:** Google Gemini (for helping me cross the finish line).

# Contributing: how we use git

New to git? That's fine. Follow these steps **every time** you work on a task.
Each step shows the **command line** version and the **GitHub Desktop** version. Use whichever you like.

**The golden rules**
- Never commit directly to `main`. `main` must always build.
- One task = one branch = one pull request (PR).
- Only change files in your own module folder unless the lead says otherwise.
- Small commits, often.

---

## The workflow

### 0. First time only: clone the repo
```bash
git clone https://github.com/<org-or-user>/<repo>.git
cd <repo>
```
GitHub Desktop: **File → Clone repository** → pick the repo → **Clone**.

### 1. Get the latest `main`
```bash
git checkout main
git pull
```
GitHub Desktop: **Current branch** → `main`, then click **Fetch origin** / **Pull origin**.

### 2. Create a branch for your task
Branch names: `feature/<short-description>` for new things, `fix/<short-description>` for bug fixes.
Use lowercase and dashes: `feature/left-motor-pwm`, `fix/imu-wrong-sign`.
```bash
git checkout -b feature/left-motor-pwm
```
GitHub Desktop: **Current branch → New branch**, type the name, make sure it's based on `main`, **Create branch**.

### 3. Work, build, and commit in small steps
Make a change → **build it** → commit. Repeat.

How to build (see [README.md](README.md) for details):
- Firmware change: `cd firmware` then `pio run` (or the ✓ in PlatformIO's bottom bar).
- Web change: `cd web` then `npm run build`.
- Testing on the robot:
  1. `node scripts/build-web.mjs` (from the repo root)
  2. PlatformIO **Upload Filesystem Image** (`pio run -t uploadfs`)
  3. PlatformIO **Upload** (`pio run -t upload`)

  ⚠️ Forgetting step 2 is the **most common mistake**: the robot keeps the old UI (or shows "Not found").
  If the UI top bar says *version mismatch*, you skipped a step.

Then commit:
```bash
git status                       # see what changed
git add firmware/src/locomotion/ # add only your files
git commit -m "locomotion: set up PWM for left motor"
```
GitHub Desktop: tick the files on the left, write a summary at the bottom-left, **Commit to feature/...**.

Good commit messages start with the area: `sensors: add IMU read`, `web: add joystick`, `comms: log client IP`.
Never commit `firmware/data/` (generated), `node_modules/`, or `secrets.h`. `.gitignore` already skips them.

### 4. Push your branch
```bash
git push -u origin feature/left-motor-pwm   # first push
git push                                    # later pushes
```
GitHub Desktop: **Publish branch** (first time), then **Push origin**.

### 5. Open a Pull Request (PR)
On GitHub, click **Compare & pull request** (or GitHub Desktop: **Branch → Create pull request**).
- Base: `main`, compare: your branch.
- Fill in **every** part of the template, including how you tested it and whether you used AI.
- Link the issue: write `Closes #12` in the description.

### 6. Review
- Wait for the **build check** to go green ✅. If it's red ❌, click **Details**, fix it, commit, and push again.
  The PR updates by itself.
- The lead (and module owner) review it. If they ask for changes, make them on the **same branch** and push.
- Don't merge your own PR without an approval.

### 7. Merge
When approved and green: **Squash and merge** on GitHub.

### 8. Delete the branch and go back to `main`
On GitHub click **Delete branch** after merging. Then locally:
```bash
git checkout main
git pull
git branch -d feature/left-motor-pwm
```
GitHub Desktop: switch to `main`, **Pull origin**, then **Branch → Delete** on the old branch.

---

## Keeping your branch up to date
If `main` changed while you were working (other people merged), bring those changes into your branch:
```bash
git checkout main
git pull
git checkout feature/left-motor-pwm
git merge main
```
GitHub Desktop: stay on your branch → **Branch → Update from main**.

---

## How to fix a merge conflict
A conflict means two people changed the same lines. Git can't guess which one is right, so you decide.

1. Git marks the conflict in the file like this:
   ```
   <<<<<<< HEAD
   your version
   =======
   the other version
   >>>>>>> main
   ```
2. Edit the file so it's correct. Often you want parts of **both**. Delete the `<<<<<<<`, `=======`, `>>>>>>>` lines.
   (VS Code shows buttons: *Accept Current*, *Accept Incoming*, *Accept Both*.)
3. **Build it** to make sure it still compiles.
4. Finish the merge:
   ```bash
   git add <the-file>
   git commit
   ```
   GitHub Desktop: it lists the conflicted files. Open each one in your editor, fix it, then click **Continue merge**.
5. Push.

Stuck? Don't guess, and don't delete other people's code. Ask the lead. Conflicts are rare if you stay in your own folder.

**Never** use `git push --force` on a shared branch, and never commit to `main`.

---

## Using AI responsibly
AI tools (Claude, Copilot, ChatGPT, Cursor, ...) are allowed and useful. But **you** are responsible for the code.

- Your AI tool must follow [AGENTS.md](AGENTS.md). Claude, Copilot and Cursor load it automatically; for
  ChatGPT or others, paste AGENTS.md into the chat first.
- **Understand every line** before you commit it. In review you must be able to explain what it does and why.
  If you can't, ask the AI to explain, or ask a teammate.
- **Test it.** It must build, and anything that moves must be tested on the bench before the wall (see [SAFETY.md](SAFETY.md)).
- **Don't trust hardware details from AI.** It will happily invent pin numbers, I2C addresses, and library
  functions. Check the datasheet and `config.h`.
- Keep AI changes small and inside your folder. If it wants to edit other folders, `config.h`, a `.h`
  interface, or the protocol (`docs/protocol.md`, `protocol.h`, `protocol.ts`), stop and ask the lead.
- Watch for AI "fixes" that remove safety code (link timeout, e-stop latch, clamping) to make something work.
  That is never OK.
- Tick the AI box in the PR template honestly. Using AI is fine; hiding it isn't.

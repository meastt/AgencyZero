# 🦞 OpenClawSEO: The "For Dummies" Guide

Welcome! If you're feeling lost, don't worry. OpenClaw is a bit different from normal programs because it lives in the **background** of your Mac, like a quiet assistant.

## 1. Is it "Running"?
Unlike a game or an app you "open," OpenClaw runs as a **Service**. 

*   **Background (The Gateway):** This is the "brain's house." It starts automatically when you turn on your Mac. You don't need to keep a terminal window open for it to work.
*   **Foreground (The Agent):** This is your SEO Manager. It wakes up every 60 minutes, does its job, and goes back to sleep.

### Important Commands to Know:
Open your terminal inside the `OpenClawSEO` folder and use these the most:

| Command | What it does |
| :--- | :--- |
| `npm start` | **Force Start:** Wake up the agent RIGHT NOW to do its daily tasks. |
| `openclaw logs --follow` | **The Matrix:** See exactly what the agent is thinking in live time. |
| `openclaw status` | **Checkup:** See if the brain (Gateway) and the agents are healthy. |

---

## 2. Using Telegram
Your bot is your "remote control" and "reporting line."

### How to talk to it:
1.  **Just Type:** You can type "Hello" or "Give me an update" or even "/start".
2.  **The Delay:** Because it uses an AI brain (Claude), it might take 5-10 seconds to respond. 
3.  **If it doesn't reply:** 
    *   Make sure your Mac is on and connected to the internet.
    *   Try running `npm start` in your terminal to "poke" the system.

---

## 3. How to fix it if it breaks
If the bot stops replying or you think it's stuck:

1.  **Restart the Brain:** Run `openclaw gateway stop` then `openclaw gateway start`.
2.  **Check the logs:** Run `openclaw logs --follow`. If you see a lot of red text, that's usually where the error is.
3.  **Check your keys:** Make sure your `.env` file hasn't accidentally lost any of your API keys.

---

## 4. What is it actually doing? 
Every hour, the agent:
1.  Looks at your **Google Search Console** for traffic drops.
2.  Researches competitors using **Brave Search**.
3.  Drafts or updates content on your **WordPress** site.
4.  Sends you a summary on **Telegram**.

**That’s it! You can now close your terminal and let the lobster do the work.** 🦞

### FAQ: Does it run when my Mac is closed?
Yes, it stops when your Mac sleeps.
- **Lid Closed/Sleep:** The agent pauses and won't send messages.
- **Lid Opened/Wake:** The agent resumes automatically and catches up on any missed checks.

### 🔋 How to run 24/7 (Amphetamine Setup)
To keep your SEO Manager working even when you close your laptop:
1.  **Start a Session:** Click the Amphetamine icon in your menu bar and select **"Indefinite"**.
2.  **Lid Closed Mode:** Go to `Amphetamine Preferences` -> `Settings` -> `Closed-Display Mode`.
3.  **Check the box:** Ensure "Allow system to sleep when display is closed" is **UNCHECKED**.
4.  **Keep it Plugged In:** MacBooks require a power adapter to stay awake with the lid closed.

Aaron Poetzel Illini MBB Transfer Portal

Problem It Solves: 

  College rosters are now made or broken in the offseason every year in the transfer portal. One of the hardest questions for a staff isn't "Who was good last year" but "How will their skill transfer to this level and will they fit with the team?" Oftentimes a high-usage scorer at a mid major will not put up the same levels at a Big Ten School. This project builds a tool that helps project a transfer's production to Illinois, and gives a GM/Staff a quick way to gain an understanding of the transfer landscape and top targets in the space.

What Data I used and How I sourced it:
  I used Bart Torvik (barttorvik.com), and exported the advanced player stats and team ratings for seasons 2022-2026. As BartTorvik blocks scraping without consent, it was easier to build a website version with a downloaded csv, but it may be possible to have the website actively update.
  I detected transfers from the data, by checking whether or not a player appeared at a different team in consecutive seasons. I couldn't find a csv for this seasons transfers, so I took ESPNs list of transfers and turned it into a CSV.

How I Built My Solution:
  I built the portal in python, with pandas and numpy for the data pipeline and scikit-learn for the model. I used Claude Code extensively for site design, and implementation once I was done building a high-level framework. I then iterated many times until the regression model and site was to a acceptable level.

  The model is a regression model of the form Stat_post = b0 + b1*Stat_pre + b2*(change in Level) + b3 * (Stat_pre * change in level) + controls. Change in level is the competition-level jump (destination adj. efficiency margin - origin). The interaction term allows for the model to penalize different player tyoes differntly.

  App: Streamlit front end, with Altair charts and a custom CSS terminal theme built in Claude.


Why it's Useful to the Illini GM or Staff:

The portal ranks players by Illini fit and can help quickly analyze large amounts of player data to find targets based off of specified skill desires. It can also help loosely predict how a players game would translate to Illinois, and hopefully help to bring new prospects to light for the Illini to jump on before other teams. (Including diamond in the rough players). 

Final product: 
GitHub: https://github.com/poetzaaron/Aaron_Poetzel_IlliniMBB
Live App: https://aaronpoetzelillinimbb.streamlit.app/

# What Summer Costs Tucson's Grid: Slide talk track (v1)

Goes with `tucson_grid.pptx` (27 slides). Voice: `Wispr Flow Tone\VOICE_Spoken.md`, technical mode. Facts:
`results.json` (demand side and Act 4) and `outages/deck/numbers.json` (storm side). Each slide opens on what is on
screen, explains it, says what it means, then hands off. Slides 14-21 reuse the outage deck's slides and most of
their talk track. About 14 minutes read aloud; Wispr check (interview mode): 10/10. `build_grid_deck.py` loads each section into that slide's speaker notes, so edit here and rebuild.

How to read it: one sentence per line, read straight through. A blank line is a pause. Lists are bullets.

---
## Slide 1 · Title  (0:30)

Hi, my name is Jake Moore, and I study Management Information Systems at the University of Arizona.
This project is about what summer does to Tucson's electric grid, and I built it from public data only.

Summer hits the grid from two sides, so I ran two studies and put them in one answer.
Every number you'll see comes straight out of the code.

## Slide 2 · Research question  (0:40)

So here's the research question.
What does summer cost Tucson's electric grid, from the heat on one side and storms on the other, and where would money do the most good?

I split it in two because the two problems are measured differently.
The heat side is about demand, so I worked in Python and SQL on hourly grid data.
The storm side is about outages, so I worked in R on outage counts every 15 minutes.
Then one script combines both into a single results file, and that's what the last section of this deck is built on.

## Slide 3 · Two sides of summer  (1:00)

This slide is the whole project on one page, and the rest of the deck walks through it.

On the left is heat.
Once it gets past about 82 degrees, every extra degree adds about 61 megawatts to the day's highest hour.
The utility's own forecast runs about 47 megawatts short on most hot days.
And because solar keeps growing, the evening climb that other power plants have to cover grew 113 megawatts in one year.

On the right is storms.
Outages cost Pima County's homes and businesses about $72.9 million a year, and July alone holds 42% of all the outage time.
Night outages also last 39% longer than daytime ones of the same size.

So the question for the end of the deck is how you compare a dollar figure on the right with megawatts on the left.

## Slide 4 · The data  (0:50)

Everything here comes from 6 free, public sources.

The grid data is EIA-930, which is the federal hourly record of demand, the utility's day-ahead forecast and what each fuel generated.
EIA-861 is the yearly filing with sales, customer counts and outage minutes.
The weather is Open-Meteo, hourly temperature, dew point, rain and wind for central Tucson.

On the storm side, EAGLE-I from Oak Ridge counts the customers out in Pima County every 15 minutes.
Berkeley Lab's survey gives what an outage costs a home or a business.
And NREL publishes what a utility battery costs, which I use as a yardstick near the end.

Everything is in Arizona time, which never changes for daylight saving, so the hours line up across all of it.

## Slide 5 · How I built it  (0:50)

This is the pipeline, left to right.

One pull script runs both data pullers with pinned end dates, so a rerun gives the same numbers.
The demand side is Python with DuckDB, and the storm side is an R Markdown paper with 4 models.
Then a combine script reads both results and builds one results file.

The last step is the one I care about most.
A checker reads the memo, this talk track and the text on these slides, pulls out every number and confirms each one is in that results file.
I tested it by planting a wrong number in a copy of the memo, and it caught it, and when it found a real number that wasn't backed by the data, I fixed the memo.

## Slide 6 · Divider: Heat  (0:10)

So I'll start with heat, which is the demand side.

## Slide 7 · Heat drives the peak  (1:15)

Each dot on this chart is one day.
Going across is the day's high temperature in Tucson, and going up is the highest hour of demand that day, which the industry calls the peak.

Below about 82 degrees, the dots are flat, because heat barely moves demand.
Above 82, air conditioning takes over and the dots climb in a straight line.
Every extra degree adds about 61 megawatts, which is about 2.2% of a typical hot-day peak.

Temperature by itself explains 91% of the day-to-day swings, which I think is a really tight fit for real data.
Two-thirds of summer days peak in the 5 to 6 PM hour.
A hot night matters too, but only about a quarter as much as a hot afternoon.

## Slide 8 · The forecast runs short on hot days  (1:15)

So if heat drives demand that cleanly, the next question is how well the utility predicts it.
Every day it publishes a day-ahead forecast, which is its prediction of demand for each hour of the next day.

Overall it's accurate, and it misses by 2.87% an hour on average.
But this chart breaks the miss on the daily peak out by temperature, and that's where the problem shows up.

On mild days it's on target.
From 90 to 105 degrees, the forecast peak comes in 1.7% low, which is about 47 megawatts.
On the 10 days at 110 or hotter, it's 4.1% low, about 134 megawatts.

And this holds even on days when the weather forecast got the temperature right.
So I think the miss is about how the forecast treats heat, and I'll come back to that at the end.

## Slide 9 · Demand is barely growing  (1:00)

Before getting to the evening, I want to show what isn't the problem in Tucson, which is growth.

A hot year uses more power than a mild one, so I compared years under the same weather.
That's what weather-adjusted means in the table on the left, and Tucson's average demand went from 2,109 megawatts in 2024 to 2,145 in 2026.

The bars on the right compare that with the two Phoenix utilities.
APS grew 10.8% since 2024, SRP 2.6%, and Tucson 1.7%.
So Phoenix kind of has a growth problem, and Tucson really doesn't.
In Tucson the pressure comes from when power is needed, which is the next section.

## Slide 10 · Divider: The evening ramp  (0:10)

So this section is about solar and the evening.

## Slide 11 · What the evening ramp is  (1:00)

This chart is an illustration, so the shapes are drawn to show the idea, not measured.

The dark line is total demand through a summer day.
The yellow area is what solar farms supply during the middle of the day.
The orange line is what's left over after solar and wind, and the industry calls that net load.

Net load is what gas and coal plants, batteries and imports actually have to cover.
In the late afternoon, solar fades while demand is still high, so net load climbs fast.
That steep climb, the thick part of the orange line, is the evening ramp.

## Slide 12 · Tucson's evening ramp grew in one year  (1:15)

Now here's the real version for Tucson, an average July and August day in 2026.

The table on the right is the story.
Solar farms covered about 20% of midday demand through 2025, and in 2026 that jumped to 31%.
So the average 3-hour climb at sunset went from 530 megawatts to 644, which is 113 more in a single year.
On the hardest days, the climb grew 181 megawatts.

The net-load peak also moved later, from about 5:30 to after 6 PM.
Batteries are probably the main tool built for this, and battery output in the top hours reached about 267 megawatts in 2026.

## Slide 13 · Divider: Storms  (0:10)

So that's the demand side, and now I'll switch to storms.

## Slide 14 · The scope of the problem  (1:15)

To show what a bad night looks like, this chart is one night, July 28th, 2023, the worst in the 6 years.

The line is the number of customers out, one point every 15 minutes, and the purple band is the 3 PM to 6 AM storm night.
It sits near zero until about 7 PM on that Friday.
Then the storm hits, and it shoots up to 54,076 customers out at once, about 12% of the county.

After the peak, it takes the rest of the night and most of Saturday to come back down.
That long tail is crews restoring one circuit at a time.

The red area under the line is customer-minutes, which is one customer without power for one minute.
Inside that storm-night window, it adds up to 26.6 million customer-minutes.

The 8 worst nights, out of more than 2,000, hold 33% of all the overnight outage time.
So a few nights drive the total, and I think planning for the average night misses where the cost is.

## Slide 15 · Monsoon season matters  (1:00)

That was one night, and this chart zooms out to the whole year.
Each bar is the total outage time for one month across all 6 years, with July and August in red.

July alone holds 42% of all the recorded outage time, and August adds another 13%.
The monsoon window, June 15th to September 30th, is under a third of the year, and it holds 66% of the outage time.

I think that timing points pretty clearly at the storms.
I want to be careful with it, though, because an outage in monsoon season isn't automatically caused by a storm.

## Slide 16 · The humidity signal  (0:50)

If storms drive this, the next question is whether you can see a bad storm coming.
This chart looks at one clue, the dew point at noon, which is how much moisture is in the air.

The left box is normal monsoon nights, and the right box is big outage nights, meaning 5,000 or more customers out at once.
On big outage nights, the median noon dew point was 59 degrees, and on normal nights it was 53.

Moisture is the fuel for a monsoon thunderstorm, and you can measure it at noon, hours before the storm shows up.

## Slide 17 · Pricing an outage  (1:30)

To put a dollar figure on outages, I started with the table on the left.
It's from Berkeley Lab, which pooled 34 utility surveys asking homes and businesses what an outage costs them.

Read across the rows, and the gap between customer types is huge.
A 1-hour outage costs a home about $5.10, a small business about $647, and a medium or large business almost $18,000.

The 3 arrows are how I turned that into a cost for each Pima County outage.
The first is the customer mix, where I estimated about 590 large business accounts from TEP's sales.
The second is length, which is customer-minutes divided by the peak number of customers out.
The third moves the survey's 2013 dollars into 2025 dollars with the Consumer Price Index.

## Slide 18 · The price tag  (1:45)

So, adding it all up, the big red number is the result.
Outages cost Pima County's homes and businesses about $72.9 million a year, as an average over 2020 to 2025.
About $49.3 million of that is monsoon season.

It's an estimate built on survey costs, and nobody measured that loss directly.
Businesses carry 96% of it, even though they're only about 1 customer in 10.

So I reran it with each assumption changed by itself, and that's the chart on the right.
The biggest bar is the share of businesses among the customers who lose power.
If businesses are half as common among them as I assumed, the cost drops to about $38 million, and if they're twice as common, it goes to about $143 million.
That's a sensitivity range, so it shows which assumption matters most, and it doesn't put odds on the answer.
I think the business mix is the first thing better data should pin down.

## Slide 19 · Slower restoration at night  (1:15)

This slide is about what goes with slower restoration, and each row is one outage event.

Restoration here is the time from the peak until the county total drops to 10% of that peak.
The top bar is the big result.
An outage that peaks at night goes with 61% longer restoration, with an interval of 31 to 99%.

Measured a second way, as the average time each customer is out, night outages run 39% longer.
That's the number I use for pricing at the end, because it matches how the cost model measures length.

What I can't say is why night outages are slower.
They're probably harder to reach in the dark, or maybe there are fewer crews on shift, and the data can't separate those.

## Slide 20 · Flagging a big night by 3 PM  (1:15)

The next question is whether a big night can be flagged by 3 PM, using only noon dew point and the afternoon high.

The chart is an ROC curve, and the closer a curve hugs the top left, the better.
The black line is the 3 PM model, with an area under the curve of 0.89.
A model that only knows the date scores 0.69, and a coin flip is 0.5.

The interval on the 0.89 runs from 0.80 to 0.98, which is wide, because there were only 10 big nights to test on.
And at the top-20% cutoff on the right, 85% of the flags are still false alarms.

## Slide 21 · Does the flag hold up?  (1:00)

So I tested it another way, by rebuilding the model on every year before a given year and testing it on that year.

In 2022 it scored 0.50, which is no better than a coin flip.
In 2023 it scored 0.77, and in 2024 it scored 0.85.
And 2025 had no big outage nights at all, so it can't be scored.

So I feel like the fair way to put it is a promising but unstable signal.
Humid, hot afternoons do go with big outage nights, but the flag isn't steady enough yet to schedule crews around.

## Slide 22 · Divider: Where the money goes  (0:10)

So now I'll put the two sides together.

## Slide 23 · Where the money goes  (1:30)

This is the chart the whole project builds to, and it has two panels on purpose.

The left panel is in dollars a year.
The dark bar is what storm outages cost customers, $72.9 million.
The blue bars are what three improvements would be worth to customers:
- 10% fewer customers hit per storm, about $7.3 million a year
- every outage restored 10% faster, about $5.5 million
- and night outages restored as fast as daytime ones, about $8.7 million.

Those are benefits only, because what each improvement would cost the utility isn't public.
The striped orange bar below the dashed line is different, because it's a cost to the utility, which I'll explain on the next slide.

The right panel is in megawatts, because that's how the demand side is measured.
It shows the forecast shortfall on hot days, the growth in the evening ramp, and the batteries already running at peak.

I feel like putting them in one ranking would make them look comparable when they aren't, because the units are different, so I kept them as two panels.

## Slide 24 · Putting the two sides side by side  (1:30)

So to connect the megawatts to dollars, I used one sourced yardstick, which is the box at the bottom.

NREL puts a 4-hour utility battery at $1,371 per kilowatt in 2025 dollars.
Spread over its 15-year life, plus 2.5% a year for upkeep, that's about $126 per kilowatt each year.
It leaves out financing, so it's a floor, and batteries are only one of the tools that can cover a ramp.

With that yardstick, the table reads like this.
Storm outages cost customers $72.9 million a year, and each fix is worth $5.5 to $8.7 million.
The 113 megawatts of new evening ramp would take about $14.2 million a year in batteries.
And the hot-day forecast gap is a modeling fix, so there's no building to price at all.

## Slide 25 · What this means  (1:15)

So here's what I take from it.

Storm outages are the biggest dollar figure on the table, and each improvement I priced is worth millions a year before its own cost.

The evening is the grid's new pressure, because one year of solar growth added a ramp worth about $14 million a year in batteries.

The forecast gap on hot days is a modeling problem, so it gets fixed in the model and not by building anything.

And both problems land on summer evenings, because storms build from mid-afternoon and the net-load peak now comes after 6 PM.
What public data can't tell me is what each fix would cost the utility, so that's the next piece a real decision would need.

## Slide 26 · Limitations and what I learned  (1:15)

There are a few limits I want to be upfront about.
The demand side covers TEP's whole grid area, and the outage side covers Pima County, which overlap but aren't the same.
The storm numbers are benefits only, and the battery yardstick is a floor.
Everything is an association, and the forecast I graded is the public one, not the utility's internal planning model.

The box on the right is what I learned.
The hard part was putting two different measurements on one page without pretending they're the same.
Outage costs are dollars to customers and the ramp is megawatts, so I showed both and gave the megawatts a sourced yardstick instead of forcing one ranking.

## Slide 27 · References  (0:20)

These are the sources, and every one of them is free and public.
The photos are from Wikimedia Commons, mostly from a Tucson photographer, and the credits are in the project files.

Thanks for watching.

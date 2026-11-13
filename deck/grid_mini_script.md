# What Summer Costs Tucson's Grid: 10-minute talk track (v1)

Goes with `tucson_grid_10min.pptx`: 13 of the 27 slides (`GRID_KEEP` in `build_grid_deck.py`), numbered 1-13 here.
Built from the matching sections of `grid_script.md`, with the hand-offs rewritten where a slide in between was cut.
About 8:45 read aloud, 10 minutes with the visuals. Wispr check (interview mode): 10/10.

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

This slide is the whole project on one page, and the next 10 slides walk through it.

On the left is heat.
Once it gets past about 82 degrees, every extra degree adds about 61 megawatts to the day's highest hour.
The utility's own forecast runs about 47 megawatts short on most hot days.
And because solar keeps growing, the evening climb that other power plants have to cover grew 113 megawatts in one year.

On the right is storms.
Outages cost Pima County's homes and businesses about $72.9 million a year, and July alone holds 42% of all the outage time.
Night outages also last 39% longer than daytime ones of the same size.

So the question for the end of the deck is how you compare a dollar figure on the right with megawatts on the left.

## Slide 4 · Heat drives the peak  (1:15)

Each dot on this chart is one day.
Going across is the day's high temperature in Tucson, and going up is the highest hour of demand that day, which the industry calls the peak.

Below about 82 degrees, the dots are flat, because heat barely moves demand.
Above 82, air conditioning takes over and the dots climb in a straight line.
Every extra degree adds about 61 megawatts, which is about 2.2% of a typical hot-day peak.

Temperature by itself explains 91% of the day-to-day swings, which I think is a really tight fit for real data.
Two-thirds of summer days peak in the 5 to 6 PM hour.
A hot night matters too, but only about a quarter as much as a hot afternoon.

## Slide 5 · The forecast runs short on hot days  (1:15)

So if heat drives demand that cleanly, the next question is how well the utility predicts it.
Every day it publishes a day-ahead forecast, which is its prediction of demand for each hour of the next day.

Overall it's accurate, and it misses by 2.87% an hour on average.
But this chart breaks the miss on the daily peak out by temperature, and that's where the problem shows up.

On mild days it's on target.
From 90 to 105 degrees, the forecast peak comes in 1.7% low, which is about 47 megawatts.
On the 10 days at 110 or hotter, it's 4.1% low, about 134 megawatts.

And this holds even on days when the weather forecast got the temperature right.
So I think the miss is about how the forecast treats heat, and I'll come back to that at the end.

## Slide 6 · Tucson's evening ramp grew in one year  (1:15)

Demand in Tucson is barely growing, only 1.7% since 2024 once weather is removed, so the pressure comes from when power is needed.
Net load is demand minus solar and wind, which is what gas plants, batteries and imports actually have to cover, and its fast climb as solar fades is the evening ramp.
This chart is an average July and August day in Tucson in 2026.

The table on the right is the story.
Solar farms covered about 20% of midday demand through 2025, and in 2026 that jumped to 31%.
So the average 3-hour climb at sunset went from 530 megawatts to 644, which is 113 more in a single year.
On the hardest days, the climb grew 181 megawatts.

The net-load peak also moved later, from about 5:30 to after 6 PM.
Batteries are probably the main tool built for this, and battery output in the top hours reached about 267 megawatts in 2026.

## Slide 7 · The scope of the problem  (1:15)

So now I'll switch to storms, and to show what a bad night looks like, this chart is one night, July 28th, 2023, the worst in the 6 years.

The line is the number of customers out, one point every 15 minutes, and the purple band is the 3 PM to 6 AM storm night.
It sits near zero until about 7 PM on that Friday.
Then the storm hits, and it shoots up to 54,076 customers out at once, about 12% of the county.

After the peak, it takes the rest of the night and most of Saturday to come back down.
That long tail is crews restoring one circuit at a time.

The red area under the line is customer-minutes, which is one customer without power for one minute.
Inside that storm-night window, it adds up to 26.6 million customer-minutes.

The 8 worst nights, out of more than 2,000, hold 33% of all the overnight outage time.
So a few nights drive the total, and I think planning for the average night misses where the cost is.

## Slide 8 · Monsoon season matters  (1:00)

That was one night, and this chart zooms out to the whole year.
Each bar is the total outage time for one month across all 6 years, with July and August in red.

July alone holds 42% of all the recorded outage time, and August adds another 13%.
The monsoon window, June 15th to September 30th, is under a third of the year, and it holds 66% of the outage time.

I think that timing points pretty clearly at the storms.
I want to be careful with it, though, because an outage in monsoon season isn't automatically caused by a storm.

## Slide 9 · The price tag  (1:45)

To price outages, I used Berkeley Lab's survey of what an outage costs homes and businesses, weighted by TEP's customers and moved to 2025 dollars.
The big red number is the result.
Outages cost Pima County's homes and businesses about $72.9 million a year, as an average over 2020 to 2025.
About $49.3 million of that is monsoon season.

It's an estimate built on survey costs, and nobody measured that loss directly.
Businesses carry 96% of it, even though they're only about 1 customer in 10.

So I reran it with each assumption changed by itself, and that's the chart on the right.
The biggest bar is the share of businesses among the customers who lose power.
If businesses are half as common among them as I assumed, the cost drops to about $38 million, and if they're twice as common, it goes to about $143 million.
That's a sensitivity range, so it shows which assumption matters most, and it doesn't put odds on the answer.
I think the business mix is the first thing better data should pin down.

## Slide 10 · Flagging a big night by 3 PM  (1:15)

The next question is whether a big night can be flagged by 3 PM, using only noon dew point and the afternoon high.

The chart is an ROC curve, and the closer a curve hugs the top left, the better.
The black line is the 3 PM model, with an area under the curve of 0.89.
A model that only knows the date scores 0.69, and a coin flip is 0.5.

The interval on the 0.89 runs from 0.80 to 0.98, which is wide, because there were only 10 big nights to test on.
And at the top-20% cutoff on the right, 85% of the flags are still false alarms.
Tested year by year, it scored 0.50 in 2022, 0.77 in 2023 and 0.85 in 2024, and 2025 had no big nights at all, so it's promising but not proven.

## Slide 11 · Where the money goes  (1:30)

So now I'll put the two sides together, and this is the chart the whole project builds to, with two panels on purpose.

The left panel is in dollars a year.
The dark bar is what storm outages cost customers, $72.9 million.
The blue bars are what three improvements would be worth to customers:
- 10% fewer customers hit per storm, about $7.3 million a year
- every outage restored 10% faster, about $5.5 million
- and night outages restored as fast as daytime ones, about $8.7 million.

Those are benefits only, because what each improvement would cost the utility isn't public.
The striped orange bar below the dashed line is different, because it's a cost to the utility, which is the next slide.

The right panel is in megawatts, because that's how the demand side is measured.
It shows the forecast shortfall on hot days, the growth in the evening ramp, and the batteries already running at peak.

I feel like putting them in one ranking would make them look comparable when they aren't, because the units are different, so I kept them as two panels.

## Slide 12 · Putting the two sides side by side  (1:30)

So to connect the megawatts to dollars, I used one sourced yardstick, which is the box at the bottom.

NREL puts a 4-hour utility battery at $1,371 per kilowatt in 2025 dollars.
Spread over its 15-year life, plus 2.5% a year for upkeep, that's about $126 per kilowatt each year.
It leaves out financing, so it's a floor, and batteries are only one of the tools that can cover a ramp.

With that yardstick, the table reads like this.
Storm outages cost customers $72.9 million a year, and each fix is worth $5.5 to $8.7 million.
The 113 megawatts of new evening ramp would take about $14.2 million a year in batteries.
And the hot-day forecast gap is a modeling fix, so there's no building to price at all.

## Slide 13 · What this means  (1:15)

So here's what I take from it.

Storm outages are the biggest dollar figure on the table, and each improvement I priced is worth millions a year before its own cost.

The evening is the grid's new pressure, because one year of solar growth added a ramp worth about $14 million a year in batteries.

The forecast gap on hot days is a modeling problem, so it gets fixed in the model and not by building anything.

And both problems land on summer evenings, because storms build from mid-afternoon and the net-load peak now comes after 6 PM.
What public data can't tell me is what each fix would cost the utility, so that's the next piece a real decision would need.
Thanks for watching.

# What Do Monsoon Power Outages Cost Tucson? 10-minute talk track

Goes with `storm_outage_cost_jakemoore_10min.pptx` (16 slides), built by `python deck/build_deck.py --mini`.
Same slides as the full deck, minus the how-it-works, cleaning and diagnostics slides. The full deck and its script
(`deck_script.md`, about 30 minutes) stay as they are.

How to read it: one sentence per line, read straight through. A blank line is a pause. Lists are bullets.

---
## Slide 1 · Title  (0:25)

Hi, my name is Jake Moore, and I study Management Information Systems at the University of Arizona.
This project is about what Tucson's monsoon power outages cost, built in R on about 210,000 outage readings.
Every number you'll see comes straight out of that code.

## Slide 2 · Research question  (0:30)

The research question has 3 parts.
What do power outages cost Pima County?
What conditions go with a severe storm night?
And can the worst nights be flagged by 3 PM, before most storms hit?
I care about that last part because some storms barely flicker the lights, and some leave 50,000 people in the dark.
I answered it with the 4 models at the bottom, and I'll show one result from each.

## Slide 3 · The data  (0:40)

Everything comes from 4 free, public sources, one per card.
The outage card is the main one.
Oak Ridge National Laboratory counts customers without power every 15 minutes, and for Pima County that's 143,825 readings.
Then there's hourly Tucson weather, NOAA storm reports, and a Berkeley Lab survey of what an outage costs homes and businesses.
I joined them all by date and hour in Arizona time, from 2020 through 2025.
Before any of that, I cleaned the data and checked the times against NOAA, so a storm in the weather data lines up with the outages it caused.

## Slide 4 · Feature engineering  (0:45)

This slide is the most important design choice I made.
Monsoon storms build in the afternoon and run past midnight, so counting by calendar day would split one storm in two.
So I built a storm night, the purple bar, from 3 PM to 6 the next morning.
The grey part is the weather a utility already knows by 3 PM, which feeds the forecast model later.
The 4 definitions at the bottom carry through the rest of the talk.
The one to remember is a big outage night, which means 5,000 or more customers out at once.

## Slide 5 · The scope of the problem  (0:40)

Here's what a bad night looks like, July 28th, 2023, the worst in the data.
The line is customers out, and it jumps from near zero to 54,076 at once, about 12% of the county.
Then it takes the rest of the night and most of the next day to come back down.
That long tail is crews fixing one circuit at a time.
The bottom bullet is the takeaway.
The 8 worst nights, out of more than 2,000, hold 33% of all the overnight outage time.
So I think planning for the average night misses where the cost really is.

## Slide 6 · Monsoon season matters  (0:30)

Zooming out to the whole year, each bar is a month.
July alone holds 42% of the outage time.
The monsoon window, June 15th to September 30th, is under a third of the year, and it holds 66%.
That timing points at the storms, though I can't prove every one of those outages was storm-caused.

## Slide 7 · Pricing an outage  (0:50)

To put a price on it, I used the Berkeley Lab table on the left, which pooled 34 utility surveys.
An hour without power costs a home about $5.10, a small business about $647, and a large business almost $18,000.
That gap matters, because a few businesses losing power can cost more than thousands of homes.
The 3 steps below the table turn it into a cost per outage:
- estimate the mix of homes and businesses from TEP's sales
- use customer-minutes divided by peak customers as the average outage length
- and move 2013 dollars to 2025 dollars.

The curve on the right is the result, and the thing to notice is that cost climbs slowly as outages get longer.

## Slide 8 · The price tag  (0:55)

Adding it up, outages cost Pima County's homes and businesses about $72.9 million a year, with about $49.3 million of that in monsoon season.
It's a modeled estimate, and businesses carry 96% of it.

Because it leans on assumptions, the chart on the right reruns it with one assumption changed at a time.
The biggest bar is the share of businesses among the customers who lose power, which can cut the cost in half or nearly double it.
Changed one at a time, the answers run from about $38 million to $143 million.
I'd call that a sensitivity range.
It shows which assumption matters most, and it doesn't put odds on where the true cost lands.
So $72.9 million is my central estimate, and the business mix is the first thing better data should pin down.

## Slide 9 · Model 1 results  (0:45)

Model 1 is a multiple linear regression that asks which weather goes with a severe storm night.
The inputs use different units, so the chart moves each one by a typical amount, 1 standard deviation, and shows the change in outage time.
A typical rise in noon dew point goes with 108% more outage time, heat with 98%, rain with 76% and gusts with 63%.
So moisture and heat matter about as much as wind and rain.
These are associations, and they don't prove cause and effect.
The model also only explains 11% of the variation.
I think part of that is the weather coming from one point, when a monsoon storm can be a few miles wide and miss it.

## Slide 10 · Model 2: Slower restoration  (0:45)

Model 2 is a second linear regression, this time on each outage event, and it asks what goes with slower restoration.
I measured restoration as the time from the peak until outages drop to 10% of that peak.
I only used the 510 events where I could actually see that happen, and the typical one took about an hour.
The top bar is the main result: an outage that peaks at night goes with 61% longer restoration, with an interval of 31 to 99%.
It held up when I dropped unusual events and when I grouped events by storm.
What I can't say is why.
It could be:
- harder access in the dark
- more lightning damage
- or fewer crews on shift.

The data can't separate those, so it's something to investigate.

## Slide 11 · ROC curve and the cutoff  (0:50)

Model 3 is a logistic regression, which predicts the chance of a yes-or-no outcome, here whether tonight becomes a big outage night.
It only uses 2 things known by 3 PM, the noon dew point and the afternoon heat.
I trained it on 2020 through 2023 and tested it on 2024 and 2025.
I split by year instead of randomly, because that's how it would really be used, built on the past and judged on the future.

The chart is an ROC curve, where the closer a line hugs the top left, the better.
The 3 PM model scored 0.89, against 0.69 for a model that only knows the date.
The table shows the catch.
At a cutoff that flags about 1 evening in 5, it caught 8 of 10 big nights, but 85% of its flags were false alarms.

## Slide 12 · Does the flag hold up?  (0:40)

10 big nights is a thin test, so I checked it another way, which is the chart on the left.
Each year, I retrained it on every year before and tested it on that one year.
It scored 0.50 in 2022, which is a coin flip, then 0.77 and 0.85, and 2025 had no big nights at all.
So the 0.89 is a best case.
The chart on the right makes the same point, because catching more big nights means even more false alarms.
I'd call it a promising but unstable signal, and not something to schedule crews around yet.

## Slide 13 · How a decision tree works  (0:35)

Model 4 is a decision tree, which trades some accuracy for rules anyone can read.
It asks 2 questions: is the noon dew point at least 42 degrees, and is it before September 1st?
If both are yes, it flags the night.
It's easy to remember, but it flags 60% of nights and scores 0.71.
So I think it's probably best as a readable companion to the logistic model.
When I let a tree grow with no limits, it scored perfectly on the training years and worse than a coin flip on the test years, so keeping it short matters.

## Slide 14 · Recommendations  (0:55)

So what does this mean for a utility?
The chart prices 4 improvements per year, as scenarios that leave out what each one would cost to do.
Cutting customers interrupted by 10% is worth about $7.3 million, against $5.5 million for restoring everything 10% faster.
I think that points to prevention as the place to start.
Cost grows with every customer hit, but only slowly as outages get longer.

The red bars are the night difference from Model 2.
I priced it on the cost model's own measure of outage length, where night outages run 39% longer.
Closing half of that would be worth about $4.7 million a year, if it can be fixed.
The utility's own crew records would show whether the cause is staffing, access or damage.
And the 3 PM flag is worth watching, but it isn't ready to act on alone.

## Slide 15 · Conclusion  (0:40)

To sum it up, outages cost Pima County about $72.9 million a year, mostly in monsoon season.
The business mix moves that number the most.
Humid, hot, windy and rainy nights are the bad ones, and night outages take longer to fix.
A 3 PM warning looks possible, but it isn't proven yet.

What I learned is that the hardest decisions were about the data, not the models.
Deciding what a missing reading means and how to measure restoration moved the results more than any algorithm did.

## Slide 16 · References  (0:10)

These are my sources, and the photo credits are on the right.
Thanks for watching.

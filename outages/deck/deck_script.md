# What Do Monsoon Power Outages Cost Tucson? Slide talk track (v4)

Goes with `storm_outage_cost_jakemoore.pptx` (34 slides). Voice: `Wispr Flow Tone\VOICE_Spoken.md`, technical mode.
Facts: `storm_outage_cost_jakemoore.Rmd` and `deck/numbers.json`. v4 rewrites every slide for flow: each one opens on
what is on screen and why it follows the last slide, explains it, says what it means, then hands off.
Each section is loaded into that slide's speaker notes by `build_deck.py`, so edit here and rebuild.

How to read it: one sentence per line, read straight through. A blank line is a pause. Lists are bullets.

---
## Slide 1 · Title  (0:35)

Hi, my name is Jake Moore, and I study Management Information Systems at the University of Arizona.
This project is about Tucson's power outages, mostly the ones that come with monsoon season.
That's when big afternoon thunderstorms roll in and knock out power across the city.

I wanted to figure out what those outages cost, and why some storm nights are so much worse than others.
I also wanted to know whether a bad night can be seen coming early enough to do something about it.

I built the whole thing in R, on about 210,000 outage readings, one every 15 minutes.
Every number you'll see comes straight out of that code.

## Slide 2 · Research question  (0:45)

So here's the research question, and it has 3 parts.

The first part is what power outages cost Pima County in dollars, meaning the homes and businesses that lose power.

The second part is what conditions go with a severe storm night.
I ask that because some storms barely flicker the lights, and some leave 50,000 people in the dark.

The third part is whether the worst nights can be flagged by 3 in the afternoon, which is before most monsoon storms hit.

At the bottom are the 4 models I used to answer it.
I'll explain how each one works when we get to it.

## Slide 3 · Introduction  (1:00)

Before the data, I want to say why this is worth doing.

On the left is the purpose, which lines up with the research question.
I wanted to put a dollar figure on outages, because outage minutes on their own don't tell a budget anything.
Then I wanted the conditions that go with a severe night and with slow restoration.
And I wanted to test whether the worst nights can be flagged early enough to act on.

Below that is why Tucson.
Tucson Electric Power, which everybody calls TEP, reported 168.7 outage minutes per customer in 2023.
106.8 of those minutes came from major storm days, so more than half the year's outage time came from a handful of storms.

That matters because fixing it costs money.
Hardening the grid means things like:
- stronger poles
- tree trimming
- and automated switches.

Every one of those budget requests has to show where it pays off, and that's the question this project is built around.

The photo on the right is what restoration looks like, a crew in a bucket truck fixing one circuit at a time.
Keep that picture in mind, because it explains a lot of what shows up later.

## Slide 4 · The data  (1:15)

To answer the question, I used 4 public data sources, one per card on this slide, all from 2020 through 2025.

The first card is outages.
That comes from a system called EAGLE-I, which Oak Ridge National Laboratory runs.
Every 15 minutes it records how many customers are without power, and for Pima County that's 143,825 readings.

The second card is weather, from a free service called Open-Meteo.
I pulled 52,608 hours of weather for central Tucson:
- temperature
- dew point
- wind gusts
- and rain.

The third card is storm reports from NOAA's Storm Events Database, which covers:
- thunderstorm wind
- hail
- lightning
- and flash floods.

There are 618 of those reports for Pima County.

The last card is cost.
That's a Berkeley Lab survey of what an outage costs homes and businesses.
I weighted it by TEP's real customer counts and electricity sales from the Energy Information Administration.

All 4 sources get joined by date and hour in Arizona time, which is 7 hours behind UTC all year because Arizona doesn't do daylight saving.

## Slide 5 · How I built it in R  (1:00)

This slide is the pipeline, the 5 steps that turn those sources into results, going left to right.

Step 1 is the pull.
The outage data comes as one national file per year, about 7 gigabytes in total.
So my script streams each file and only keeps the Pima County rows.

Step 2 is cleaning, with the tidyverse and lubridate packages, and I'll walk through that on the next slide.
Step 3 is building the features the models use, which is the slide after that.

Step 4 is the models.
I used lm for the linear regressions, glm for the logistic regression and rpart for the tree.
Then broom, car, pROC and caret pull out the results and run the checks.

Step 5 is the report, an R Markdown paper with every chart drawn in ggplot2.

The code at the bottom is one real line from the cleaning step, the one that moves outage times from UTC to Arizona time.
And the box on the right is the reason I built it this way.
Every number on these slides comes from the code, so if the data changes, I rerun one file and everything updates.

## Slide 6 · Data cleaning  (1:45)

This is step 2, the cleaning.
The staircase on the right shows the steps in order, and the bullets on the left give the numbers for each one.

To start, I removed 1,321 readings that had no customer count.
I also dropped 3 readings that landed outside 2020 to 2025 once the times were shifted.

Next, I converted the time zone, because EAGLE-I records everything in UTC.
I didn't just trust the conversion, so I checked it against NOAA.
On July 14th, 2024, outages in the data crossed 1,000 customers at 5:45 PM Arizona time.
NOAA logged thunderstorm wind in Tucson at that same minute, so the times line up.

The last step is the one I had to rethink, which is missing readings.
EAGLE-I only writes a row when somebody is out, so a missing 15 minutes usually means nobody was out.
That's why I filled missing intervals with zero.
But the dataset's own documentation says a missing row can also be a gap in the data collection, and from the file alone you can't tell which.

So I flagged the suspicious ones.
If 500 or more customers were out and the readings just stop, that's more likely a reporting gap.
Power comes back circuit by circuit, so it's unlikely everyone came back in the same 15 minutes.
That rule flagged 3,165 intervals.

If I fill those in instead of using zero, total outage time goes up about 18%.
That's not small, so I carried it into the cost range later, and I kept those gaps out of the restoration model.

## Slide 7 · Feature engineering  (1:30)

This is step 3, building the features, and I think it's the most important design decision in the project.

The bar across the top is a timeline from noon to 6 the next morning.
Monsoon storms build in the afternoon, and a lot of them run past midnight.
If I counted by calendar day, one storm would get split across 2 days, and both halves would look smaller than the real thing.

So I built what I call a storm night, the purple part of the bar.
It runs from 3 in the afternoon to 6 the next morning, so one storm stays in one row.

The grey part, before 3 PM, is the weather a utility would already know by mid-afternoon:
- the noon dew point
- the high temperature so far
- and the gusts and rain so far.

That becomes the input for Model 3.

The 4 definitions at the bottom carry through the rest of the deck.
Customer-minutes is one customer without power for one minute, so it's the area under the outage curve.
A big outage night is 5,000 or more customers out at the same time, about 1.1% of the county.
An outage event is a run of 500 or more customers out that peaks at 1,000 or more, and there are 596 of those.
And restoration time is the hours from an event's peak until the number of customers out drops to 10% of that peak.
I'll come back to why that last one matters in Model 2.

## Slide 8 · Section: Exploring the data  (0:10)

With the data cleaned and the storm nights built, the next section looks at what the data shows before any models.

## Slide 9 · The scope of the problem  (1:15)

To show what a bad night looks like, this chart is one night, July 28th, 2023, the worst in the 6 years.

The line is the number of customers out, one point every 15 minutes, and the purple band is the 3 PM to 6 AM storm night.
It sits near zero until about 7 PM on that Friday.
Then the storm hits, and it shoots up to 54,076 customers out at once, about 12% of the county.

After the peak, it takes the rest of the night and most of Saturday to come back down.
That long tail is the crews from the earlier photo, restoring one circuit at a time.

The red area under the line is the customer-minutes from the last slide.
Inside that storm-night window, it adds up to 26.6 million customer-minutes.

The bottom bullet is the big takeaway from this section.
The 8 worst nights, out of more than 2,000, hold 33% of all the overnight outage time.
So a few nights drive the total, and I think planning for the average night misses where the cost is.

## Slide 10 · Monsoon season matters  (1:00)

That was one night, and this chart zooms out to the whole year.
Each bar is the total outage time for one month across all 6 years, with July and August in red.

July alone holds 42% of all the recorded outage time, and August adds another 13%.
The official monsoon window, June 15th to September 30th, is under a third of the year, and it holds 66% of the outage time.

I think that timing points pretty clearly at the storms.
I want to be careful with it, though, because an outage in monsoon season isn't automatically caused by a storm.
Equipment fails in summer too, and one of the 8 worst nights had almost no wind and no storm reports at all.

## Slide 11 · The humidity signal  (1:00)

If storms drive this, the next question is whether you can see a bad storm coming.
This chart looks at one clue, the dew point at noon, which is how much moisture is in the air.

It's a box plot.
Each box is the middle half of the nights, and the line inside it is the median.
The left box is normal monsoon nights, and the right box is big outage nights.

On big outage nights, the median noon dew point was 59 degrees.
On normal monsoon nights, it was 53.

Moisture is the fuel for a monsoon thunderstorm, and you can measure it at noon, hours before the storm shows up.
That's the idea Model 3 tests, which is the box at the bottom right.

## Slide 12 · Cross-check against TEP  (1:00)

Before putting a price on any of this, I wanted to make sure the outage data is believable.
So this slide compares it with what TEP reports to the federal government every year.

The table shows outage minutes per customer by year, with the county data in the middle and TEP's filing on the right.
They rise and fall together, and 2023 is the worst year in both, at 232.5 minutes in the county data and 168.7 in TEP's filing.

The county number runs higher in 5 of the 6 years, and I think there are probably 3 reasons:
- Pima County also includes Trico Electric Co-op's customers, not just TEP's.
- EAGLE-I takes a snapshot every 15 minutes instead of tracking each customer.
- And utilities are allowed to leave some events out of their filing.

So I'd call this a check on direction.
It shows the data follows the real pattern, but it doesn't prove the exact numbers.

## Slide 13 · Section: What does an outage cost?  (0:10)

Now that the data checks out, this section puts a price on the outages and then tests how sure that price is.

## Slide 14 · Pricing an outage  (1:45)

To price an outage, I started with the table on the left.
It's from Berkeley Lab, which pooled 34 surveys that 10 utilities ran between 1989 and 2012.
They asked homes and businesses what an outage costs them in things like:
- spoiled food
- lost sales
- and staff sitting around.

Read across the rows, and you can see the gap between customer types is huge.
A 1-hour outage costs a home about $5.10.
It costs a small business about $647, and a medium or large business almost $18,000.

The 3 arrows below the table are how I turned that into a cost for each Pima County outage.

The first arrow is the customer mix, and this one needed care.
Berkeley Lab splits small and large businesses by how much electricity they use, and TEP doesn't publish its accounts that way.
So I estimated it.
If TEP's businesses look like the survey's average businesses, about 590 large accounts would make TEP's total business sales add up.
That's an estimate, and it also assumes the customers who lose power look like TEP's customers overall.

The second arrow is length.
For each outage event, I divide customer-minutes by the peak number of customers out, which gives an average time without power.
It's a stand-in, because a long storm can hit different customers at different times.

The third arrow is moving the survey's 2013 dollars into 2025 dollars, using the Consumer Price Index, a factor of 1.382.

The chart on the right is the cost per customer by outage length, after those steps.
Notice that it climbs pretty slowly as outages get longer.
That shape matters later, in the recommendations.

## Slide 15 · The price tag  (2:30)

So, adding it all up, the big red number is the result.
Outages cost Pima County's homes and businesses about $72.9 million a year, as an average over 2020 to 2025.

That number covers every qualifying outage in the year.
The monsoon season part is about $49.3 million, and even that is a seasonal total, because I can't confirm every one of those outages was a storm.

It's also an estimate built on survey costs and a few stand-ins, and nobody measured that loss directly.
Businesses carry 96% of it, even though they're only about 1 customer in 10.
An hour without power costs a home a few dollars and a large business thousands, so the businesses dominate.

Because the estimate leans on assumptions, I reran it with each assumption changed by itself.
That's the chart on the right.
Each bar shows how far the total moves when one assumption changes.

The biggest bar is the share of businesses among the customers who lose power.
If businesses are half as common among them as I assumed, the cost drops 48%.
If they're twice as common, it nearly doubles.
I think that makes sense, because businesses carry almost all the cost.

The other bars move it less:
- Halving or doubling the number of large accounts moves it from minus 11 to plus 22%.
- Making outages a quarter shorter or longer moves it about 20% either way.
- And filling in the uncertain gaps adds 16%.

Changed one at a time, the answers run from about $38 million to $143 million.
I'd call that a sensitivity range.
It shows which assumptions matter most, and it doesn't put odds on where the true cost lands.
If every assumption moves the same direction at once, the gap gets even wider, about $28 million to $242 million.
So $72.9 million is my central estimate, and the business mix is the first thing better data should pin down.

## Slide 16 · Section: Linear regression  (0:10)

That's the price.
The next 2 models are linear regressions, and they look at what goes with a bad night and what goes with slow restoration.

## Slide 17 · How multiple linear regression works  (1:30)

Model 1 asks which weather conditions go with a severe storm night, and this slide explains how the method works.

The chart on the right is the simple version.
Each dot is one of 648 monsoon nights, with the noon dew point across the bottom and the outage time going up.
The red line is the straight line that fits those dots best.

Multiple linear regression does the same thing with several inputs at once, and that's the equation in the box.
The outcome is outage time for each storm night.
There are 4 inputs:
- peak wind gust
- rain
- noon dew point
- and the daily high temperature.

Each b in the equation is a coefficient.
It says how much outage time changes with that input while the other 3 stay the same.

The bullets explain 2 choices I made.
The first one is that I used the log of outage time, because most nights are near zero and a few are in the millions.
On a log scale, each coefficient reads as a percent change, which is easier to talk about.

The other one is that I left the NOAA storm reports out on purpose.
In Arizona, a thunderstorm wind report often gets filed because the wind knocked a power line down.
So using those reports to predict outages would be circular.

## Slide 18 · Model 1 results  (1:45)

These are the Model 1 results.

The 4 inputs use different units:
- degrees
- miles per hour
- and inches.

So instead of comparing them raw, the chart moves each input by 1 standard deviation, which is one typical-sized change.
Each red dot is the percent change in outage time, and the grey line through it is the 95% interval.

A typical rise in noon dew point, about 11.5 degrees, goes with 108% more outage time.
The daily high goes with 98% more, rain with 76% and gusts with 63%.
So I feel like heat and moisture look about as important as wind and rain.
I'd keep that loose, though, because the intervals are wide, and overlapping intervals don't prove 2 effects are the same size.

These are associations.
The model shows those conditions show up together with bad nights, but it doesn't prove one more degree would cause a set amount of outage time.

The model also only explains about 11% of the night-to-night variation, which is the R squared of 0.11, and that's weak.
One likely reason is that the weather comes from a single point in central Tucson.
A monsoon storm can be a few miles wide, so it can flatten lines in Marana while that point stays dry.
I can't prove that's the main reason, though, because other things vary too:
- which lines are exposed
- what actually broke
- and how outages get reported.

## Slide 19 · Diagnostics  (1:15)

Before trusting Model 1, I ran 2 standard checks, one on each side of this slide.

The table on the left is the variance inflation factor, or VIF.
It measures how much each input overlaps with the others.
If 2 inputs move together, the model can't tell which one deserves the credit.
Anything under 5 is fine, and all 4 here are under 2, so each result can be read on its own.

The chart on the right shows the residuals, meaning how far off the model was for each night.
Ideally, that's an even cloud around zero, and mostly it is.

The exception is the diagonal edge in the bottom left.
Those are nights with almost no outages, sitting on a floor the line can't go below.
A straight line struggles with something that's often zero, and that's one reason Model 3 asks a simple yes-or-no question instead.

## Slide 20 · Model 2: Slower restoration  (2:00)

Model 2 uses the same method on a different question, which is what goes with slower restoration.
Here, each row is one outage event instead of one night, and the outcome is the log of restoration hours.

First I had to settle how to measure restoration.
The data only gives one total for the whole county, so I can't follow individual customers.
Restoration is the time from the peak until that total drops to 10% of the peak.
That's an approximation, because new outages can start while old ones are being fixed.

I only kept events where that drop was actually observed.
86 events had one of the uncertain gaps in the middle, so I set them aside, which left 510 events.
The median one took about an hour to get down to 10% of its peak.

Setting events aside can bias a model if the ones you drop are the bad ones, so I compared the 2 groups.
The set-aside events are about the same size and peak at night about as often.
They're less often in monsoon season, and together they're only 8% of the cost.
So it probably doesn't hide the worst events, but strictly this model describes the events I could measure.

The chart shows how each input goes with restoration time, as a percent change with its interval.
The top one is the big result.
An outage that peaks at night, between 8 PM and 6 AM, goes with 61% longer restoration, with an interval of 31 to 99%.
Monsoon season goes with 36% longer, and twice as many customers out goes with 16% longer.

I checked whether a few unusual events were driving the night result.
Dropping the most influential events gave 69%.
One storm can also produce several events, so I grouped the errors by storm date, and the interval stayed about 31 to 99%.
So the night result holds up.

What I can't say is why night outages are slower.
There are a few possible reasons:
- they're harder to reach in the dark
- they could involve more lightning damage
- or there might be fewer crews on shift.

The data can't separate those, so the night difference is something worth investigating, and it isn't a measured staffing effect.

## Slide 21 · Section: Logistic regression  (0:10)

The first 2 models looked back at what happened.
Model 3 looks ahead, and asks whether a big outage night can be flagged by 3 PM.

## Slide 22 · How logistic regression works  (1:30)

This slide explains the method behind Model 3, which is logistic regression.

Linear regression predicts an amount, like outage minutes.
Logistic regression predicts the chance of a yes-or-no outcome.
Here, the outcome is whether tonight becomes a big outage night, with 5,000 or more customers out at once.

The chart shows how that works.
Across the bottom is the noon dew point, and going up is the predicted chance of a big night, with afternoon heat held at its typical value.
The model still fits a straight line, but it fits it to the odds of a yes, and then bends that line into this S-shaped curve.
That keeps every prediction between 0 and 100%.

You can see the curve sits near zero below about 40 degrees, and then it climbs fast as the air gets more humid.
The small ticks along the bottom are the 24 big nights in the training years, and almost all of them sit on the humid side.

The results come out as odds ratios, which say how much one more degree multiplies the odds of a big night.

I picked the 2 inputs, moisture and heat, before testing anything, because that's what fuels a monsoon thunderstorm.

I also removed 4 days where 5,000 or more customers were still out at 2:45 PM, the last reading before 3.
On those days, the big outage is already happening, so predicting it would be cheating.
Earlier, I was removing any day with a big outage that morning, even if it was fixed by noon.
That threw out days where the night was still an open question, and fixing it added 1 big night to the test years.

## Slide 23 · Train-test split by time  (1:30)

To judge Model 3 fairly, it has to be tested on data it never saw, and this slide shows how I split it.

In the flight delay project I did before this one, I split the data randomly, 80% to train and 20% to test.
That works for most problems, but not for data over time.
A random split could let the model learn from July 14th, 2024 and then get tested on July 15th, which is basically an open-book test.

So the boxes across the top split by year.
The grey years, 2020 through 2023, are for training, and the red years, 2024 and 2025, are for testing.
That's how it would really be used, built on the past and judged on the future.
It comes out to 430 monsoon nights to train on with 24 big ones, and 214 nights to test on with 10 big ones.

The box on the right is the result of training.
Each degree of noon dew point multiplies the odds of a big night by 1.15, and each degree of afternoon heat by 1.17.
With only 24 big nights, letting an algorithm pick the inputs would mostly chase noise.
I did try all 7 available inputs as a comparison, and it scored 0.89 on the test years, no better than the 2.

## Slide 24 · Confusion matrix  (1:45)

Now the test.
The table on the left is a confusion matrix, which compares what the model flagged against what actually happened in 2024 and 2025.

The dark boxes are where the model got it right.
It left 160 quiet nights alone, and it caught 8 of the big nights.
The lighter boxes are its mistakes.
It missed 2 big nights, and it raised 44 false alarms.

The table on the right turns those counts into rates.
Sensitivity is 80%, meaning it caught 8 of the 10 big nights.
Specificity is 78%, meaning it left 160 of 204 quiet nights alone.

I think the rate that matters most here is precision.
The flag went up 52 times, and only 8 of those were real, which is 15%.
That's about 6.5 flags for every big night it catches.

The box at the bottom is why I don't use plain accuracy.
Only 5% of nights were big, so a model that always says no would be 95% accurate and still catch nothing.

## Slide 25 · ROC curve and the cutoff  (1:30)

The confusion matrix used one cutoff, and this slide shows what happens across all of them.

The chart is an ROC curve.
Going up is the share of big nights caught, and going across is the share of quiet nights falsely flagged.
The dotted line is a coin flip, and the closer a curve hugs the top left, the better.

The black line is the 3 PM model, with an area under the curve, or AUC, of 0.89.
The red dashed line is a model that only knows the date, at 0.69.
The 95% interval on the 0.89 runs from 0.80 to 0.98.
That's wide, because there were only 10 big nights to test on, so I wouldn't lean too hard on the 0.89.

The table on the right compares 2 cutoffs, meaning 2 rules for when to raise the flag.
The balanced cutoff caught all 10 big nights, but it flagged 116 nights, more than half the season, and only 9% of those flags were real.
The top-20% cutoff flags about 1 evening in 5 and catches 8, but 85% of its flags are still false alarms.

## Slide 26 · Does the flag hold up?  (1:30)

One test period with 10 big nights is thin, so I tested it another way.
For each year, I rebuilt the model on every year before it and tested it on that one year.
That's called rolling-origin validation, and it's the chart on the left.

In 2022, trained on just 2 years, it scored 0.50, which is no better than a coin flip.
In 2023 it scored 0.77, and in 2024 it scored 0.85.
And 2025 had no big outage nights at all, so it can't be scored, and every flag that year was a false alarm.
That means the 0.89 from the last slide is a best case, earned mostly on 2024.

The chart on the right is precision against recall.
Going across is the share of big nights caught, and going up is the share of flags that were real.
As you try to catch more big nights, more of the flags turn out to be false, and the dot is my cutoff at 15%.

So I feel like the fair way to put it is a promising but unstable signal.
Humid, hot afternoons do go with big outage nights, but the flag isn't steady enough yet to schedule anything around.

## Slide 27 · Section: Decision tree  (0:10)

The logistic model is accurate but hard to explain in a sentence.
Model 4 is a decision tree, which trades some accuracy for rules anyone can read.

## Slide 28 · How a decision tree works  (1:30)

The chart on the left is the tree itself, so I'll read it from the top down.

A decision tree asks a series of yes-or-no questions and sorts each night into one of the boxes at the bottom, called leaves.
Each question is picked to split the nights into groups that are as clean as possible, ideally all big nights or all quiet ones.
That cleanness is measured with something called the Gini index.

This tree asks 2 questions.
The top question is whether the noon dew point is at least 42 degrees.
If it is, the next question is whether it's before September 1st.
If both answers are yes, it flags the night.
I count dates on a 365-day calendar, so September 1st is the same cutoff in leap years too.

The bullets on the right cover how I built it.
Left alone, a tree keeps splitting until it memorizes the data, so it gets pruned back.
To decide how far to prune, I tested each size of tree on whole seasons it didn't train on, for the same reason I split by year in Model 3.
And because big nights are rare, I told the tree to weigh both outcomes equally, so the percentages in the leaves are weighted and aren't real odds.

The box at the bottom right is the rule card and how it did.
It's easy to remember, but I think it's probably too broad to use on its own.
It flags 60% of test nights, against 24% for the logistic model, and it scores 0.71 against 0.89.
So it's a different model with its own trade-off, and it isn't just the logistic model written as rules.

## Slide 29 · Overfitting  (1:15)

That pruning step matters a lot, and this chart shows why.
For each model, the grey bar is the AUC on the training years, and the red bar is the AUC on the test years it never saw.

The third pair is the tree with no limits at all.
It kept splitting until almost every leaf was pure, which took 41 leaves built on just 24 big training nights.
It scored a perfect 1.00 on the years it learned from, and 0.48 on the test years, which is worse than a coin flip.
It memorized 2020 through 2023 instead of learning what makes a big night.

Pruning fixes that.
Testing on one held-out season at a time cut the tree down to 3 leaves, the same rule card from the last slide.

The logistic model and the rule card both hold up on the test years, and I think that's the main lesson here.
Logistic regression ranks the nights better, and the tree gives up some accuracy for rules anyone can repeat.

## Slide 30 · Recommendations  (2:30)

So what does all of this mean for a utility?
This chart uses the cost model to price 4 improvements, in dollars per year.
They're scenarios, not forecasts, and none of them include what the improvement would cost to make.

The green bar is prevention.
Cutting the number of customers interrupted by 10% is worth about $7.3 million a year.
The grey bar is speed.
Restoring every outage 10% faster is worth about $5.5 million.
I think prevention wins because of the cost curve from earlier.
Cost grows slowly as outages get longer, but it grows in direct proportion to how many customers lose power.
So prevention is where I'd start looking, though it doesn't settle which project to fund.

The red bars are the night difference from Model 2, and I had to be careful pricing them.
Model 2 measured the time until the outage drops to 10% of its peak, but the cost model uses the average length of the outage.
Those 2 move together, with a correlation of about 0.74, but they aren't the same thing.
A few hundred customers left out for hours keep adding cost after the 10% point, and that's probably where the gap comes from.
So I measured the night difference directly on average length, and it's 39%, not the 61% from Model 2.

Priced that way, closing the whole night difference would be worth about $8.7 million a year, and closing half of it about $4.7 million.
That's only if it can be fixed.
The next step is the utility's own crew schedules and outage records, which would show whether the cause is:
- staffing
- access
- or damage.

The last point on the right is the 3 PM flag.
In the test years, night outages after a flagged afternoon held 83% of that half-difference value.
So if more crews in the evening turn out to help, the flag shows which evenings to try first.
With 15% precision and a coin-flip 2022, though, I wouldn't schedule crews around it yet.

## Slide 31 · Limitations  (1:00)

Those recommendations come with limits, and these are the 7 I want to be upfront about.

The data covers the whole county, so it includes Trico Electric Co-op's customers along with TEP's.
Missing readings can be zero or a reporting gap, and filling the suspicious ones adds about 18% to outage time.
The weather comes from one point, which is one likely reason Model 1 only explains 11% of the variation.
There are only 34 big nights in 6 seasons, and none in 2025.
None of the models prove cause and effect, including the night restoration difference.
The cost rests on assumptions, the business mix most of all, and on survey data from 1989 to 2012.
And the weather data was rebuilt after the fact, so the 3 PM flag shows whether the idea works.
It still needs a test with the data a utility really had at 3 PM.

## Slide 32 · Future work and implications  (1:00)

Each of those limits points to a next step, and these are the ones I'd take first.

The first is better cost inputs.
Berkeley Lab released version 2.2 of its outage cost calculator in February 2026, with newer survey data.
And TEP's real count of business customers by size would replace my estimate.

The second is real weather forecasts.
Open-Meteo's archive of day-ahead forecasts only goes back to January 2024 for most models, which is too short to train on.
But it also keeps older short-range forecasts, NOAA's HRRR model back to 2018 and GFS back to March 2021, including storm energy and gusts.
Training on those would probably be the best test of the flag, because it uses information a utility really had at 3 PM.

The third is going below the county level.
Circuit-level outage and crew data, which only the utility has, would test the night difference directly.

Even with the current limits, the analysis gives a utility a mid-afternoon risk signal and a structured way to compare prevention with restoration speed.
Both of those get stronger with the utility's own data.

## Slide 33 · Conclusion  (1:15)

To sum it up, outages cost Pima County an estimated $72.9 million a year, with about $49 million of it in monsoon season.
The business mix moves that number more than anything else.

The severe nights go with:
- heat
- moisture
- wind
- and rain.

Outages that peak at night take about 61% longer to restore.
And a hot, humid afternoon is a promising but unstable warning sign, not reliable enough yet to act on by itself.

The box at the bottom is what I took away from this.
I think the hardest part wasn't picking a model.
It was the decisions about the data:
- what a missing reading means
- how to measure restoration from county totals
- how many large businesses TEP serves
- and whether 2 ways of measuring outage length can stand in for each other.

Those choices moved the results more than any algorithm did, and getting them wrong the first time is what taught me that.

## Slide 34 · References  (0:15)

On the left are my references, the data sources, the 2 Berkeley Lab cost studies, and the guides I used for logistic regression and ROC curves.
The Tucson storm photos are by a photographer who goes by A Guy Named Nyal, and the credits are on the right.
Thanks for watching.

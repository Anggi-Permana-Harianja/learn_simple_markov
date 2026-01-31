//@version=5
indicator("AMT Orderflow Profile + Imbalance Highlight + Dashboard", overlay = true, max_boxes_count = 500)

// === Inputs ===
ptype = input.string("Comparison", "Profile Type", ["Comparison", "Net Order Flow"])
plook = input.int(10, "Profile Lookback")
res   = input.int(20, "Profile Resolution")
scale = input.int(10, "Profile Horizontal Scale")
off   = input.int(6,  "Profile Horizontal Offset")

h  = input.bool(true, "Show Profile", group="Appearance")

green = input.color(#00ffbb, "Buy Color", group="Appearance")
red   = input.color(#ff1100, "Sell Color", group="Appearance")

// === Imbalance Threshold ===
binImbalanceThreshold = input.float(0.75, "Bin Imbalance Threshold", minval = 0.6, maxval = 0.95)

// === Arrays ===
var boxes = array.new_box()

topB  = array.new_float(res)
botB  = array.new_float(res)
topS  = array.new_float(res)
botS  = array.new_float(res)

binBuy  = array.new_float(res)
binSell = array.new_float(res)

highs = array.new_float()
lows  = array.new_float()
buys  = array.new_float()
sells = array.new_float()

// === Collect lookback ===
highs.clear(), lows.clear(), buys.clear(), sells.clear()
for i = 0 to plook
    highs.push(high[i])
    lows.push(low[i])
    buys.push(close[i] > open[i] ? volume[i] : 0)
    sells.push(open[i] > close[i] ? volume[i] : 0)

// === Cleanup ===
while boxes.size() > 0
    boxes.shift().delete()

maxx = array.max(highs)
minn = array.min(lows)
step = (maxx - minn) / res
size = array.size(highs)

// === Bin BUY volumes ===
topB.clear(), botB.clear(), binBuy.clear()
for i = 0 to res - 1
    bottom = minn + i * step
    top    = minn + (i + 1) * step
    botB.push(bottom)
    topB.push(top)

    sumBuy = 0.0
    for j = 0 to size - 1
        inBin = not (lows.get(j) > top or highs.get(j) < bottom)
        sumBuy += inBin ? buys.get(j) : 0

    binBuy.push(sumBuy)

// === Bin SELL volumes ===
topS.clear(), botS.clear(), binSell.clear()
for i = 0 to res - 1
    bottom = minn + i * step
    top    = minn + (i + 1) * step
    botS.push(bottom)
    topS.push(top)

    sumSell = 0.0
    for j = 0 to size - 1
        inBin = not (lows.get(j) > top or highs.get(j) < bottom)
        sumSell += inBin ? sells.get(j) : 0

    binSell.push(sumSell)

// === Draw Profile + Track Text Presence ===
int buyStreak  = 0
int sellStreak = 0
bool buyTextPresent  = false
bool sellTextPresent = false

maxBuy  = array.max(binBuy)
maxSell = array.max(binSell)

for i = 0 to res - 1
    buyVol  = binBuy.get(i)
    sellVol = binSell.get(i)
    total   = buyVol + sellVol

    buyImb  = total > 0 and buyVol  / total >= binImbalanceThreshold
    sellImb = total > 0 and sellVol / total >= binImbalanceThreshold

    buyStreak  := buyImb  ? buyStreak + 1  : 0
    sellStreak := sellImb ? sellStreak + 1 : 0

    if buyStreak >= 3
        buyTextPresent := true
    if sellStreak >= 3
        sellTextPresent := true

    buyTxt  = buyImb  ? "BUY IMB\n"  + str.tostring(buyVol,  format.volume)
                      : str.tostring(buyVol, format.volume)

    sellTxt = sellImb ? "SELL IMB\n" + str.tostring(sellVol, format.volume)
                      : str.tostring(sellVol, format.volume)

    buyWidth = maxBuy > 0 ? (buyVol / maxBuy) * scale : 0
    buyRight = bar_index + off + scale
    buyLeft  = buyRight - buyWidth

    sellWidth = maxSell > 0 ? (sellVol / maxSell) * scale : 0
    sellLeft  = bar_index + off + scale
    sellRight = sellLeft + sellWidth

    if h
        boxes.push(box.new(int(buyLeft),  topB.get(i), int(buyRight), botB.get(i), border_width = buyImb ? 2 : 1, border_color = buyImb ? color.new(green,0) : color.new(green,50),  bgcolor      = buyImb ? color.new(green,75) : color.new(green,90), text         = buyTxt,  text_color   = chart.fg_color))

        boxes.push(box.new(int(sellLeft), topS.get(i), int(sellRight), botS.get(i), border_width = sellImb ? 2 : 1, border_color = sellImb ? color.new(red,0) : color.new(red,50), bgcolor      = sellImb ? color.new(red,75) : color.new(red,90), text         = sellTxt, text_color   = chart.fg_color))

// === Fresh Print Alert Logic ===
var bool prevBuyTextPresent  = false
var bool prevSellTextPresent = false

newBuyAlert  = buyTextPresent  and not prevBuyTextPresent
newSellAlert = sellTextPresent and not prevSellTextPresent

prevBuyTextPresent  := buyTextPresent
prevSellTextPresent := sellTextPresent

// === Alert Conditions ===
alertcondition(newBuyAlert,  "BUY IMB (3+ boxes, fresh)",  "Fresh BUY imbalance printed across at least 2 boxes")
alertcondition(newSellAlert, "SELL IMB (3+ boxes, fresh)", "Fresh SELL imbalance printed across at least 2 boxes")

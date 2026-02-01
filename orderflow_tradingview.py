//@version=5
indicator("AMT Orderflow Profile + Imbalance Highlight + Dashboard", overlay = true, max_boxes_count = 500)

// === Inputs ===
ptype = input.string("Comparison", "Profile Type", options = ["Comparison", "Net Order Flow"])
plook = input.int(10, "Profile Lookback", minval = 1)
res   = input.int(20, "Profile Resolution", minval = 2, maxval = 200)
scale = input.int(10, "Profile Horizontal Scale", minval = 1)
off   = input.int(6,  "Profile Horizontal Offset", minval = 0)

h  = input.bool(true, "Show Profile", group="Appearance")

green = input.color(#00ffbb, "Buy Color", group="Appearance")
red   = input.color(#ff1100, "Sell Color", group="Appearance")

// === Imbalance Threshold ===
binImbalanceThreshold = input.float(0.75, "Bin Imbalance Threshold", minval = 0.6, maxval = 0.95)

// === Arrays ===
var box[]   boxes   = array.new_box()

var float[] topB    = array.new_float()
var float[] botB    = array.new_float()
var float[] topS    = array.new_float()
var float[] botS    = array.new_float()

var float[] binBuy  = array.new_float()
var float[] binSell = array.new_float()

var float[] highs   = array.new_float()
var float[] lows    = array.new_float()
var float[] buys    = array.new_float()
var float[] sells   = array.new_float()

// === Collect lookback ===
array.clear(highs)
array.clear(lows)
array.clear(buys)
array.clear(sells)

for i = 0 to plook
    array.push(highs, high[i])
    array.push(lows,  low[i])
    array.push(buys,  close[i] > open[i] ? volume[i] : 0.0)
    array.push(sells, open[i] > close[i] ? volume[i] : 0.0)

// === Cleanup drawn boxes ===
while array.size(boxes) > 0
    b = array.shift(boxes)
    box.delete(b)

// === Range + step (guard flat range) ===
maxx = array.max(highs)
minn = array.min(lows)
rng  = maxx - minn
step = rng != 0.0 ? (rng / res) : syminfo.mintick

size = array.size(highs)

// === Bin BUY volumes ===
array.clear(topB)
array.clear(botB)
array.clear(binBuy)

for i = 0 to res - 1
    bottom = minn + i * step
    top    = minn + (i + 1) * step
    array.push(botB, bottom)
    array.push(topB, top)

    float sumBuy = 0.0
    for j = 0 to size - 1
        lo = array.get(lows, j)
        hi = array.get(highs, j)
        inBin = not (lo > top or hi < bottom)
        sumBuy += inBin ? array.get(buys, j) : 0.0

    array.push(binBuy, sumBuy)

// === Bin SELL volumes ===
array.clear(topS)
array.clear(botS)
array.clear(binSell)

for i = 0 to res - 1
    bottom = minn + i * step
    top    = minn + (i + 1) * step
    array.push(botS, bottom)
    array.push(topS, top)

    float sumSell = 0.0
    for j = 0 to size - 1
        lo = array.get(lows, j)
        hi = array.get(highs, j)
        inBin = not (lo > top or hi < bottom)
        sumSell += inBin ? array.get(sells, j) : 0.0

    array.push(binSell, sumSell)

// === Draw Profile + Track Text Presence ===
int  buyStreak  = 0
int  sellStreak = 0
bool buyTextPresent  = false
bool sellTextPresent = false

maxBuy  = array.max(binBuy)
maxSell = array.max(binSell)

for i = 0 to res - 1
    buyVol  = array.get(binBuy, i)
    sellVol = array.get(binSell, i)

    total = buyVol + sellVol

    buyImb  = total > 0 and buyVol  / total >= binImbalanceThreshold
    sellImb = total > 0 and sellVol / total >= binImbalanceThreshold

    buyStreak  := buyImb  ? buyStreak + 1  : 0
    sellStreak := sellImb ? sellStreak + 1 : 0

    if buyStreak >= 3
        buyTextPresent := true
    if sellStreak >= 3
        sellTextPresent := true

    buyTxt  = buyImb  ? "BUY IMB\n"  + str.tostring(buyVol,  format.volume) : str.tostring(buyVol,  format.volume)
    sellTxt = sellImb ? "SELL IMB\n" + str.tostring(sellVol, format.volume) : str.tostring(sellVol, format.volume)

    buyWidth  = maxBuy  > 0 ? (buyVol  / maxBuy)  * scale : 0.0
    sellWidth = maxSell > 0 ? (sellVol / maxSell) * scale : 0.0

    buyRight = bar_index + off + scale
    buyLeft  = buyRight - buyWidth

    sellLeft  = bar_index + off + scale
    sellRight = sellLeft + sellWidth

    if h
        bBuy = box.new(int(buyLeft), array.get(topB, i), int(buyRight), array.get(botB, i), border_width = buyImb ? 2 : 1, border_color = buyImb ? color.new(green, 0) : color.new(green, 50), bgcolor = buyImb ? color.new(green, 75) : color.new(green, 90), text = buyTxt, text_color = chart.fg_color)
        array.push(boxes, bBuy)

        bSell = box.new(int(sellLeft), array.get(topS, i), int(sellRight), array.get(botS, i), border_width = sellImb ? 2 : 1, border_color = sellImb ? color.new(red, 0) : color.new(red, 50), bgcolor = sellImb ? color.new(red, 75) : color.new(red, 90), text = sellTxt, text_color = chart.fg_color)
        array.push(boxes, bSell)

// === Fresh Print Alert Logic ===
var bool prevBuyTextPresent  = false
var bool prevSellTextPresent = false

newBuyAlert  = buyTextPresent  and not prevBuyTextPresent
newSellAlert = sellTextPresent and not prevSellTextPresent

prevBuyTextPresent  := buyTextPresent
prevSellTextPresent := sellTextPresent

// === Alert Conditions ===
alertcondition(newBuyAlert,  "BUY IMB (3+ bins, fresh)",  "Fresh BUY imbalance printed across at least 3 bins")
alertcondition(newSellAlert, "SELL IMB (3+ bins, fresh)", "Fresh SELL imbalance printed across at least 3 bins")

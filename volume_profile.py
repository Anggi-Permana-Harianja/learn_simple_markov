//@version=5
indicator("Volume Profile - POC + Value Area", overlay=true, max_lines_count=500)

// ============================================================================
// INPUTS
// ============================================================================

lookback = input.int(50, "Lookback Bars", minval=20, maxval=200, group="Profile Settings")
resolution = input.int(24, "Price Bins (Resolution)", minval=10, maxval=50, group="Profile Settings")
valueAreaPct = input.float(70, "Value Area %", minval=60, maxval=80, group="Profile Settings")

showPOC = input.bool(true, "Show POC Line", group="Display")
showVA = input.bool(true, "Show Value Area", group="Display")
showHistogram = input.bool(true, "Show Volume Histogram", group="Display")

pocColor = input.color(color.new(color.yellow, 0), "POC Color", group="Colors")
vaColor = input.color(color.new(color.blue, 70), "Value Area Color", group="Colors")
histColor = input.color(color.new(color.gray, 50), "Histogram Color", group="Colors")

// ============================================================================
// CALCULATE VOLUME PROFILE
// ============================================================================

var line[] lines = array.new_line()
var box[] boxes = array.new_box()
var label[] labels = array.new_label()

var float poc = na
var float vah = na
var float val = na

if barstate.islast
    // Clear old drawings
    while array.size(lines) > 0
        line.delete(array.shift(lines))
    while array.size(boxes) > 0
        box.delete(array.shift(boxes))
    while array.size(labels) > 0
        label.delete(array.shift(labels))
    
    // Get price range
    float maxPrice = high[0]
    float minPrice = low[0]
    
    for i = 1 to lookback
        if high[i] > maxPrice
            maxPrice := high[i]
        if low[i] < minPrice
            minPrice := low[i]
    
    // Calculate bin size
    priceRange = maxPrice - minPrice
    binSize = priceRange / resolution
    
    // Prevent division by zero
    if binSize == 0
        binSize := syminfo.mintick
    
    // Create arrays for bins
    var float[] binPrices = array.new_float()
    var float[] binVolumes = array.new_float()
    
    array.clear(binPrices)
    array.clear(binVolumes)
    
    // Initialize bins
    for i = 0 to resolution - 1
        array.push(binPrices, minPrice + i * binSize)
        array.push(binVolumes, 0.0)
    
    // Distribute volume into bins
    for i = 0 to lookback
        barHigh = high[i]
        barLow = low[i]
        barVol = volume[i]
        
        // Find which bins this bar overlaps
        for j = 0 to resolution - 1
            binBottom = array.get(binPrices, j)
            binTop = binBottom + binSize
            
            // Calculate overlap
            overlapBottom = math.max(barLow, binBottom)
            overlapTop = math.min(barHigh, binTop)
            overlap = math.max(0, overlapTop - overlapBottom)
            
            if overlap > 0
                barRange = barHigh - barLow
                proportion = barRange > 0 ? overlap / barRange : 0
                volumeToAdd = barVol * proportion
                
                currentVol = array.get(binVolumes, j)
                array.set(binVolumes, j, currentVol + volumeToAdd)
    
    // Find POC (bin with highest volume)
    float maxVol = 0
    int pocIndex = 0
    
    for i = 0 to resolution - 1
        vol = array.get(binVolumes, i)
        if vol > maxVol
            maxVol := vol
            pocIndex := i
    
    poc := array.get(binPrices, pocIndex) + binSize / 2
    
    // Calculate Value Area
    totalVolume = 0.0
    for i = 0 to resolution - 1
        totalVolume += array.get(binVolumes, i)
    
    targetVolume = totalVolume * (valueAreaPct / 100)
    
    // Start from POC and expand up/down
    var int[] vaIndices = array.new_int()
    array.clear(vaIndices)
    array.push(vaIndices, pocIndex)
    
    float vaVolume = array.get(binVolumes, pocIndex)
    int upperIndex = pocIndex
    int lowerIndex = pocIndex
    
    // Expand value area
    while vaVolume < targetVolume and (upperIndex < resolution - 1 or lowerIndex > 0)
        float upperVol = upperIndex < resolution - 1 ? array.get(binVolumes, upperIndex + 1) : 0
        float lowerVol = lowerIndex > 0 ? array.get(binVolumes, lowerIndex - 1) : 0
        
        if upperVol >= lowerVol and upperIndex < resolution - 1
            upperIndex += 1
            array.push(vaIndices, upperIndex)
            vaVolume += upperVol
        else if lowerIndex > 0
            lowerIndex -= 1
            array.push(vaIndices, lowerIndex)
            vaVolume += lowerVol
        else
            break
    
    // Set VAH and VAL
    vah := array.get(binPrices, upperIndex) + binSize
    val := array.get(binPrices, lowerIndex)
    
    // ===== DRAW POC =====
    if showPOC
        pocLine = line.new(
             bar_index - lookback,
             poc,
             bar_index + 10,
             poc,
             color = pocColor,
             width = 3,
             style = line.style_solid
             )
        array.push(lines, pocLine)
        
        pocLabel = label.new(
             bar_index + 8,
             poc,
             "POC",
             style = label.style_label_left,
             color = pocColor,
             textcolor = color.black,
             size = size.small
             )
        array.push(labels, pocLabel)
    
    // ===== DRAW VALUE AREA =====
    if showVA
        vahLine = line.new(
             bar_index - lookback,
             vah,
             bar_index + 10,
             vah,
             color = vaColor,
             width = 2,
             style = line.style_dashed
             )
        array.push(lines, vahLine)
        
        valLine = line.new(
             bar_index - lookback,
             val,
             bar_index + 10,
             val,
             color = vaColor,
             width = 2,
             style = line.style_dashed
             )
        array.push(lines, valLine)
        
        // Value area box
        vaBox = box.new(
             bar_index - lookback,
             vah,
             bar_index + 10,
             val,
             border_color = color.new(vaColor, 70),
             bgcolor = color.new(vaColor, 90),
             border_width = 1
             )
        array.push(boxes, vaBox)
        
        vahLabel = label.new(
             bar_index + 8,
             vah,
             "VAH",
             style = label.style_label_left,
             color = vaColor,
             textcolor = color.white,
             size = size.tiny
             )
        array.push(labels, vahLabel)
        
        valLabel = label.new(
             bar_index + 8,
             val,
             "VAL",
             style = label.style_label_left,
             color = vaColor,
             textcolor = color.white,
             size = size.tiny
             )
        array.push(labels, valLabel)
    
    // ===== DRAW HISTOGRAM =====
    if showHistogram
        maxVolForScale = array.max(binVolumes)
        histogramWidth = 15
        
        for i = 0 to resolution - 1
            vol = array.get(binVolumes, i)
            price = array.get(binPrices, i)
            
            if vol > 0
                barWidth = (vol / maxVolForScale) * histogramWidth
                
                histBox = box.new(
                     bar_index + 12,
                     price,
                     bar_index + 12 + int(barWidth),
                     price + binSize,
                     border_color = color.new(histColor, 30),
                     bgcolor = color.new(histColor, 70),
                     border_width = 1
                     )
                array.push(boxes, histBox)

// ============================================================================
// DASHBOARD
// ============================================================================

var table dash = table.new(position.bottom_right, 2, 6, bgcolor=color.new(color.black, 85), border_width=2)

if barstate.islast
    // Determine position
    position = ""
    posColor = color.gray
    
    if not na(poc) and not na(vah) and not na(val)
        if close > vah
            position := "ABOVE VA ⬆️"
            posColor := color.orange
        else if close < val
            position := "BELOW VA ⬇️"
            posColor := color.aqua
        else if close > poc
            position := "Upper VA"
            posColor := color.green
        else if close < poc
            position := "Lower VA"
            posColor := color.red
        else
            position := "AT POC"
            posColor := color.yellow
    
    // Header
    table.cell(dash, 0, 0, "VOLUME", text_color=color.white, bgcolor=color.new(color.purple, 60))
    table.cell(dash, 1, 0, "PROFILE", text_color=color.white, bgcolor=color.new(color.purple, 60))
    
    // Position
    table.cell(dash, 0, 1, "Position", text_color=color.white, text_size=size.small)
    table.cell(dash, 1, 1, position, text_color=posColor, text_size=size.small)
    
    // POC
    table.cell(dash, 0, 2, "POC", text_color=color.white, text_size=size.small)
    if not na(poc)
        pocDist = ((close - poc) / close) * 100
        pocText = str.tostring(poc, "#.##") + "\n" + str.tostring(pocDist, "+#.#;-#.#") + "%"
        table.cell(dash, 1, 2, pocText, text_color=color.yellow, text_size=size.tiny)
    else
        table.cell(dash, 1, 2, "N/A", text_color=color.gray)
    
    // VAH
    table.cell(dash, 0, 3, "VAH", text_color=color.white, text_size=size.small)
    if not na(vah)
        vahDist = ((vah - close) / close) * 100
        vahText = str.tostring(vah, "#.##") + "\n+" + str.tostring(vahDist, "#.#") + "%"
        table.cell(dash, 1, 3, vahText, text_color=color.blue, text_size=size.tiny)
    else
        table.cell(dash, 1, 3, "N/A", text_color=color.gray)
    
    // VAL
    table.cell(dash, 0, 4, "VAL", text_color=color.white, text_size=size.small)
    if not na(val)
        valDist = ((close - val) / close) * 100
        valText = str.tostring(val, "#.##") + "\n-" + str.tostring(valDist, "#.#") + "%"
        table.cell(dash, 1, 4, valText, text_color=color.blue, text_size=size.tiny)
    else
        table.cell(dash, 1, 4, "N/A", text_color=color.gray)
    
    // Lookback
    table.cell(dash, 0, 5, "Period", text_color=color.gray, text_size=size.tiny)
    table.cell(dash, 1, 5, str.tostring(lookback) + " bars", text_color=color.gray, text_size=size.tiny)

// ============================================================================
// PLOTS FOR ALERTS
// ============================================================================

plot(poc, "POC", color.new(color.yellow, 90), 2, plot.style_circles)
plot(vah, "VAH", color.new(color.blue, 90), 2, plot.style_circles)
plot(val, "VAL", color.new(color.blue, 90), 2, plot.style_circles)

// ============================================================================
// ALERTS
// ============================================================================

var bool wasAboveVA = false
var bool wasBelowVA = false
var bool wasAtPOC = false

aboveVA = not na(vah) and close > vah
belowVA = not na(val) and close < val
atPOC = not na(poc) and math.abs(close - poc) / close < 0.005

alertcondition(aboveVA and not wasAboveVA, "Price Above Value Area", "Price moved above Value Area High")
alertcondition(belowVA and not wasBelowVA, "Price Below Value Area", "Price moved below Value Area Low")
alertcondition(atPOC and not wasAtPOC, "Price at POC", "Price reached Point of Control")

wasAboveVA := aboveVA
wasBelowVA := belowVA
wasAtPOC := atPOC

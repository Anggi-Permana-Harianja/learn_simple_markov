//@version=5
indicator("S/R - Manual Detection (WORKS!)", overlay=true, max_lines_count=100)

// ============================================================================
// INPUTS
// ============================================================================

lookback = input.int(100, "Lookback Bars", minval=50, maxval=300)
swingLength = input.int(5, "Swing Length", minval=3, maxval=15)
maxLevels = input.int(5, "Max Levels Each Side", minval=3, maxval=10)

supportCol = input.color(color.green, "Support Color")
resistanceCol = input.color(color.red, "Resistance Color")

// ============================================================================
// FIND SWING LOWS & HIGHS MANUALLY
// ============================================================================

var line[] lines = array.new_line()
var label[] labels = array.new_label()
var float[] supports = array.new_float()
var float[] resistances = array.new_float()

if barstate.islast
    // Clear
    while array.size(lines) > 0
        line.delete(array.shift(lines))
    while array.size(labels) > 0
        label.delete(array.shift(labels))
    
    array.clear(supports)
    array.clear(resistances)
    
    // Scan bars manually
    for i = swingLength to lookback
        if i >= bar_index
            break
        
        // Check if bar i is a swing LOW (lower than neighbors)
        isSwingLow = true
        centerLow = low[i]
        
        for j = 1 to swingLength
            if low[i - j] <= centerLow or low[i + j] <= centerLow
                isSwingLow := false
                break
        
        if isSwingLow
            array.push(supports, centerLow)
        
        // Check if bar i is a swing HIGH (higher than neighbors)
        isSwingHigh = true
        centerHigh = high[i]
        
        for j = 1 to swingLength
            if high[i - j] >= centerHigh or high[i + j] >= centerHigh
                isSwingHigh := false
                break
        
        if isSwingHigh
            array.push(resistances, centerHigh)
    
    // Remove duplicates & filter
    var float[] validSup = array.new_float()
    array.clear(validSup)
    
    if array.size(supports) > 0
        for i = 0 to array.size(supports) - 1
            level = array.get(supports, i)
            if level < close
                isDupe = false
                if array.size(validSup) > 0
                    for j = 0 to array.size(validSup) - 1
                        if math.abs(level - array.get(validSup, j)) < close * 0.01
                            isDupe := true
                            break
                if not isDupe
                    array.push(validSup, level)
    
    // Sort (highest first)
    if array.size(validSup) > 1
        for i = 0 to array.size(validSup) - 1
            if i + 1 < array.size(validSup)
                for j = i + 1 to array.size(validSup) - 1
                    if array.get(validSup, j) > array.get(validSup, i)
                        temp = array.get(validSup, i)
                        array.set(validSup, i, array.get(validSup, j))
                        array.set(validSup, j, temp)
    
    // Draw supports
    if array.size(validSup) > 0
        for i = 0 to math.min(array.size(validSup) - 1, maxLevels - 1)
            level = array.get(validSup, i)
            l = line.new(bar_index - 50, level, bar_index + 20, level, color=supportCol, width=2)
            array.push(lines, l)
            
            lbl = label.new(bar_index + 15, level, "S", style=label.style_label_left, color=supportCol, textcolor=color.white)
            array.push(labels, lbl)
    
    // Same for resistances
    var float[] validRes = array.new_float()
    array.clear(validRes)
    
    if array.size(resistances) > 0
        for i = 0 to array.size(resistances) - 1
            level = array.get(resistances, i)
            if level > close
                isDupe = false
                if array.size(validRes) > 0
                    for j = 0 to array.size(validRes) - 1
                        if math.abs(level - array.get(validRes, j)) < close * 0.01
                            isDupe := true
                            break
                if not isDupe
                    array.push(validRes, level)
    
    // Sort (lowest first)
    if array.size(validRes) > 1
        for i = 0 to array.size(validRes) - 1
            if i + 1 < array.size(validRes)
                for j = i + 1 to array.size(validRes) - 1
                    if array.get(validRes, j) < array.get(validRes, i)
                        temp = array.get(validRes, i)
                        array.set(validRes, i, array.get(validRes, j))
                        array.set(validRes, j, temp)
    
    // Draw resistances
    if array.size(validRes) > 0
        for i = 0 to math.min(array.size(validRes) - 1, maxLevels - 1)
            level = array.get(validRes, i)
            l = line.new(bar_index - 50, level, bar_index + 20, level, color=resistanceCol, width=2)
            array.push(lines, l)
            
            lbl = label.new(bar_index + 15, level, "R", style=label.style_label_left, color=resistanceCol, textcolor=color.white)
            array.push(labels, lbl)
    
    // Find nearest
    var float nearSup = na
    var float nearRes = na
    
    nearSup := na
    if array.size(validSup) > 0
        nearSup := array.get(validSup, 0)
    
    nearRes := na
    if array.size(validRes) > 0
        nearRes := array.get(validRes, 0)
    
    // Dashboard
    var table t = table.new(position.top_right, 2, 5, bgcolor=color.new(color.black, 80), border_width=2)
    
    table.cell(t, 0, 0, "S/R", text_color=color.white, bgcolor=color.blue)
    table.cell(t, 1, 0, "LEVELS", text_color=color.white, bgcolor=color.blue)
    
    table.cell(t, 0, 1, "Price", text_color=color.white)
    table.cell(t, 1, 1, str.tostring(close, "#.##"), text_color=color.yellow)
    
    table.cell(t, 0, 2, "Support", text_color=color.white)
    if not na(nearSup)
        dist = ((close - nearSup) / close) * 100
        table.cell(t, 1, 2, str.tostring(nearSup, "#.##") + "\n-" + str.tostring(dist, "#.#") + "%", text_color=color.green, text_size=size.small)
    else
        table.cell(t, 1, 2, "None", text_color=color.gray)
    
    table.cell(t, 0, 3, "Resistance", text_color=color.white)
    if not na(nearRes)
        dist = ((nearRes - close) / close) * 100
        table.cell(t, 1, 3, str.tostring(nearRes, "#.##") + "\n+" + str.tostring(dist, "#.#") + "%", text_color=color.red, text_size=size.small)
    else
        table.cell(t, 1, 3, "None", text_color=color.gray)
    
    table.cell(t, 0, 4, "Found", text_color=color.gray, text_size=size.tiny)
    table.cell(t, 1, 4, str.tostring(array.size(supports)) + "S/" + str.tostring(array.size(resistances)) + "R", text_color=color.white, text_size=size.tiny)

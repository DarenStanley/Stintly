import streamlit as st

# Password protection for the app
def check_password():
    def password_entered():
        if st.session_state["password"] == "MeAmBarbarian":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if check_password():
    # Your app code here
    st.write("Welcome to the private app!")

check_password()

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import datetime
import matplotlib.colors as mcolors
import numpy as np

dawn_duration = 60  # minutes
dusk_duration = 60  # minutes

def blend_colors(color1, color2, t):
    """Blend two hex colors by a factor t (0.0-1.0)."""
    rgb1 = np.array(mcolors.to_rgb(color1))
    rgb2 = np.array(mcolors.to_rgb(color2))
    return mcolors.to_hex((1-t)*rgb1 + t*rgb2)

def minutes_to_hhmmss(minutes):
    h = int(minutes // 60)
    m = int(minutes % 60)
    s = int((minutes - int(minutes)) * 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def format_minutes(value):
    mins = int(value)
    secs = int(round((value - mins) * 60))
    return f"{mins}m {secs:02d}s"


# === Settings ===
st.set_page_config(layout="wide")
st.sidebar.header("Race Settings")

drivers = ["Scott", "George", "Daren", "Chris", "Andy", "Josh"]
colors = {
    "Daren": "#383838", "George": "#f54aec", "Scott": "#c5b30c",
    "Chris": "#89c4f5", "Andy": "#ff9933", "Josh": "#299b1a",
    "Pitstop": "#FF0000"
}

baseline_stint = st.sidebar.number_input("Baseline stint time (min)", 30, 180, 100)
baseline_pit = st.sidebar.number_input(
    "Baseline pitstop time (min)", 
    min_value=0.0, max_value=30.0, value=3.0, step=0.25
)
st.sidebar.markdown(f"Stint default: **{format_minutes(baseline_stint)}**")
st.sidebar.markdown(f"Pitstop default: **{format_minutes(baseline_pit)}**")
st.sidebar.markdown("---")

start_time_input = st.sidebar.time_input("Race start time", value=datetime.time(12, 0))
sunrise_time = st.sidebar.time_input("Sunrise time", value=datetime.time(6, 0))
sunset_time = st.sidebar.time_input("Sunset time", value=datetime.time(22, 0))


race_start_minutes = start_time_input.hour * 60 + start_time_input.minute
sunrise_minutes = sunrise_time.hour * 60 + sunrise_time.minute
sunset_minutes = sunset_time.hour * 60 + sunset_time.minute


# === Driver Assignment ===
st.header("Stintly")
with st.expander("Stint Schedule", expanded=True):
    stints = []
    total_time = 0
    stint_num = 1


    while total_time < 1440:  # 24h = 1440 minutes
        st.subheader(f"Stint {stint_num}")
        col1, col2, col3 = st.columns(3)
        with col1:
            driver = st.selectbox(f"Driver for Stint {stint_num}", drivers, key=f"driver_{stint_num}")
        with col2:
            stint_override = st.number_input(f"Stint time (default: {baseline_stint})", 10, 180, value=baseline_stint, key=f"stint_{stint_num}")
        with col3:
            pit_override = st.number_input(
                f"Pit time (default: {baseline_pit})", 
                min_value=0.0, max_value=30.0, value=baseline_pit, step=0.25, key=f"pit_{stint_num}"
            )  

        # Calculate absolute start and end times in minutes since midnight
        stint_start_abs = (total_time + race_start_minutes) % 1440
        stint_end_abs = (total_time + stint_override + pit_override + race_start_minutes) % 1440

        # Format as HH:MM:SS
        start_label = minutes_to_hhmmss(stint_start_abs)
        end_label = minutes_to_hhmmss(stint_end_abs)

        st.markdown(
            f"<h4 style='color:{colors[driver]}; margin-bottom:0'>Stint Times ({start_label} - {end_label})</h3>",
            unsafe_allow_html=True
        )

        stints.append({
            "stint_num": stint_num,
            "driver": driver,
            "stint_time": stint_override,
            "pit_time": pit_override,
            "start_time": total_time,
            "end_time": total_time + stint_override + pit_override
        })
        
        total_time += stint_override + pit_override
        actual_total_time = stints[-1]["end_time"] if stints else 0
        # print(f"Total time so far: {total_time} minutes for {stint_num} stints or {actual_total_time} minutes actual time")
        stint_num += 1

# === Pitstop Count ===
pitstop_count = sum(1 for stint in stints if stint["pit_time"] > 0)
st.sidebar.markdown("---")
st.sidebar.subheader("Total Pitstops")
st.sidebar.text(f"{pitstop_count} pitstops")

# === Margin Calculation (fixed) ===
race_duration = 1440  # Total race time in minutes
actual_total_time = stints[-1]["end_time"] if stints else 0
margin = actual_total_time -baseline_pit - race_duration
# print(f"Actual total time: {actual_total_time} minutes, Margin: {margin} minutes")

if margin < 0:
    st.sidebar.error(f"Undercooked by {margin * -1} min")
else:
    st.sidebar.subheader("Time Margin")
    st.sidebar.text(f"{margin} min")


# === Driver Time Summary ===
st.sidebar.header("Total Driving Time")

# Tally up stint times per driver
from collections import defaultdict
driver_totals = defaultdict(int)

for stint in stints:
    driver_totals[stint["driver"]] += stint["stint_time"]  # only driving time, not pit

# Display in sidebar
for driver in drivers:
    minutes = driver_totals.get(driver, 0)
    hours = minutes // 60
    mins = minutes % 60
    st.sidebar.text(f"{driver}: {hours}h {mins}m")






# === Visualization ===
with st.expander("Race Schedule", expanded=True):

    def plot_schedule(stints, start_min, end_min, title, race_start_minutes):
        fig, ax = plt.subplots(figsize=(10, 1.2))
        current = start_min
        # --- Day/Night Bar ---
        # y=1 for the day/night bar, y=0 for the stints
        bar_height = 0.3
        day_color = "#16ecec"   # blue for day
        night_color = "#111111" # black for night

        # Calculate the start and end of the segment in absolute minutes
        seg_start = start_min + race_start_minutes
        seg_end = end_min + race_start_minutes

        # Handle wrap-around at midnight
        def is_day(minute):
            if sunrise_minutes < sunset_minutes:
                return sunrise_minutes <= (minute % 1440) < sunset_minutes
            else:
                # For cases where sunset is after midnight (e.g., sunset at 2:00)
                return not (sunset_minutes <= (minute % 1440) < sunrise_minutes)

        # Draw the bar in small segments for a gradient effect
        step = 2  # minutes per segment for smoother gradient
        for t in range(start_min, end_min, step):
            abs_minute = (t + race_start_minutes) % 1440

            # Calculate color for this segment
            if sunrise_minutes < sunset_minutes:
                # Normal day
                if sunrise_minutes <= abs_minute < sunrise_minutes + dawn_duration:
                    # Dawn gradient: night -> day
                    t_blend = (abs_minute - sunrise_minutes) / dawn_duration
                    color = blend_colors(night_color, day_color, t_blend)
                elif sunset_minutes - dusk_duration <= abs_minute < sunset_minutes:
                    # Dusk gradient: day -> night
                    t_blend = (abs_minute - (sunset_minutes - dusk_duration)) / dusk_duration
                    color = blend_colors(day_color, night_color, t_blend)
                elif sunrise_minutes + dawn_duration <= abs_minute < sunset_minutes - dusk_duration:
                    color = day_color
                else:
                    color = night_color
            else:
                # Sunset is after midnight (e.g., sunset at 2:00)
                if abs_minute >= sunrise_minutes and abs_minute < (sunrise_minutes + dawn_duration) % 1440:
                    t_blend = (abs_minute - sunrise_minutes) / dawn_duration
                    color = blend_colors(night_color, day_color, t_blend)
                elif abs_minute >= (sunset_minutes - dusk_duration) % 1440 and abs_minute < sunset_minutes:
                    t_blend = (abs_minute - (sunset_minutes - dusk_duration)) / dusk_duration
                    color = blend_colors(day_color, night_color, t_blend)
                elif (sunrise_minutes + dawn_duration) % 1440 <= abs_minute < (sunset_minutes - dusk_duration) % 1440:
                    color = day_color
                else:
                    color = night_color

            ax.barh(1.5, min(step, end_min - t), left=t - start_min, height=bar_height, color=color, edgecolor=color)



        for stint in stints:
            s_start = stint["start_time"]
            s_end = stint["end_time"]

            if s_end <= start_min or s_start >= end_min:
                continue  # skip stints outside this window

            # Clamp to window
            seg_start = max(s_start, start_min)
            seg_end = min(s_end, end_min)

            # Duration and segments
            stint_duration = stint["stint_time"]
            pit_duration = stint["pit_time"]
            total = stint_duration + pit_duration

            # Segment drawing
            bar_start = max(seg_start, s_start)
            bar_end = min(seg_end, s_start + stint_duration)
            stint_bar_height = 2
            if bar_start < bar_end:
                ax.barh(0, bar_end - bar_start, left=bar_start - start_min, height=stint_bar_height, color=colors[stint["driver"]])
                # Calculate label position and only show if space is sufficient
                stint_length = bar_end - bar_start
                if stint_length >= 10:  # Only label if the bar is wide enough
                    label_x = (bar_start + bar_end) / 2 - start_min
                    ax.text(label_x, 0, f'{stint["stint_time"]} min', ha='center', va='top', fontsize=10, color='white')
            
            # Bar positioning
            bar_start_pos = bar_start - start_min
            bar_width = bar_end - bar_start

            # Only label if the bar is wide enough
            if bar_width >= 10:
                # Convert times to absolute race time in minutes
                start_abs = (stint["start_time"] + race_start_minutes) % 1440
                end_abs = (stint["end_time"] - stint["pit_time"] + race_start_minutes) % 1440

                # Format as HH:MM
                start_label = f"{start_abs // 60:02.0f}:{start_abs % 60:02.0f}"
                end_label = f"{end_abs // 60:02.0f}:{end_abs % 60:02.0f}"

                # Position the text near the edges of the bar
                ax.text(bar_start_pos + 2, 0.4, start_label, ha='left', va='bottom', fontsize=8, color='white')
                ax.text(bar_start_pos + bar_width - 2, 0.4, end_label, ha='right', va='bottom', fontsize=8, color='white')


            # Pitstop
            pit_start = s_start + stint_duration
            pit_end = s_end
            if pit_start < seg_end and pit_start >= seg_start:
                
                ax.barh(0, min(pit_end, seg_end) - pit_start, left=pit_start - start_min, height=stint_bar_height, color=colors["Pitstop"])





        # Set ticks every 30 minutes
        tick_interval = 30
        tick_positions = list(range(0, end_min - start_min + 1, tick_interval))
        
        tick_labels = []
        for t in tick_positions:
            absolute_minutes = start_min + t + race_start_minutes
            hours = (absolute_minutes // 60) % 24
            minutes = absolute_minutes % 60
            tick_labels.append(f"{hours:02d}:{minutes:02d}")
        ax.set_xlim(0, end_min - start_min)
        ax.set_ylim(-1, 2)
        ax.set_title(title)
        ax.set_yticks([])
        ax.set_xlabel("Minutes")
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels)
        return fig


    # Split into 4 charts (0-360, 360-720, etc.)
    for i in range(4):
        start = i * 360
        end = (i + 1) * 360
        fig = plot_schedule(stints, start, end, f"Hour {start//60}-{end//60}", race_start_minutes)
        st.pyplot(fig)


    # === Legend ===
    st.subheader("Legend")
    legend_patches = [mpatches.Patch(color=colors[d], label=d) for d in drivers]
    legend_patches.append(mpatches.Patch(color=colors["Pitstop"], label="Pitstop"))
    st.pyplot(plt.figure(figsize=(10, 0.5)))
    plt.legend(handles=legend_patches, loc='center', ncol=4)
    plt.axis('off')
    st.pyplot(plt)

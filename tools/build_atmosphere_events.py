"""Festival definitions shared by the atmosphere and play builds."""
import os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FESTIVALS = {n: json.load(open(os.path.join(ROOT, 'assets/events', n + '.json'))) for n in ('fest_awakening', 'fest_fireflies', 'fest_forgotten', 'fest_silent_tide')}

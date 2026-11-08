import math
L=262
def hb_wl(u):
    if u<0: return 0.0
    if u<100: return 19.45*math.sqrt(max(0.0,1-(1-u/100)**2.2))
    if u<=185: return 19.45
    return 19.45*(1-0.45*((min(u,L)-185)/77)**1.8)
def y_bottom(u):
    if u<=215: return -11
    return -11+8*((u-215)/47)
def deck(u):
    if u<55: return 8+5.5*((55-u)/55)**1.5
    if u<=207: return 8
    return 6
def stem(y):
    return 4-0.35*y if y>=0 else 4+0.6*(-y)
def hb(u,y):
    base=hb_wl(u)
    if y<0:
        v=max(0.0,1-u/70)*0.8 + (max(0.0,(u-200)/62)*0.6)
        base*=1-((-y)/11)**1.3*v
        r=4.0; dy=(-7-y)
        if dy>0: base-= r-math.sqrt(max(0.0,r*r-min(dy,r)**2))
    else:
        base+=0.35*max(0.0,1-u/90)*y
    return base
def in_bulb(x,y,u):
    return ((u-4)/6.5)**2+((y+6.5)/2.8)**2+(x/3.2)**2<=1
def solid():
    H=set()
    for u in range(-3,L+1):
        for y in range(-11,15):
            for x in range(-21,22):
                if in_bulb(x,y,u): H.add((x,y,-u)); continue
                if u<0 or u>L: continue
                if y<y_bottom(u)-0.01 or y>deck(u)+0.01: continue
                if u<stem(y): continue
                if abs(x)<=hb(u,y)-0.25: H.add((x,y,-u))
    return H

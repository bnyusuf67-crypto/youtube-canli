package main

import "time"

const (
	ListenAddr   = ":8050"
	YTTimeout    = 30 * time.Second
	CacheTTL     = 5 * time.Minute
	UserAgent    = "VLC/3.0.20"
	YTDLPCommand = "yt-dlp"
)

package main

import (
	"sync"
	"time"
)

type CacheItem struct {
	URL       string
	ExpiresAt time.Time
}

type Cache struct {
	mu    sync.RWMutex
	items map[string]CacheItem
}

var cache = Cache{
	items: make(map[string]CacheItem),
}

func GetCache(slug string) (string, bool) {

	cache.mu.RLock()
	item, ok := cache.items[slug]
	cache.mu.RUnlock()

	if !ok {
		return "", false
	}

	if time.Now().After(item.ExpiresAt) {

		cache.mu.Lock()
		delete(cache.items, slug)
		cache.mu.Unlock()

		return "", false
	}

	return item.URL, true
}

func SetCache(slug string, url string) {

	cache.mu.Lock()

	cache.items[slug] = CacheItem{
		URL:       url,
		ExpiresAt: time.Now().Add(CacheTTL),
	}

	cache.mu.Unlock()
}

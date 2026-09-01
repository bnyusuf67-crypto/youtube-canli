package main

import (
	"log"
	"net/http"
)

func LiveHandler(w http.ResponseWriter, r *http.Request) {

	slug := r.URL.Path[len("/live/"):]

	ch, ok := Channels[slug]

	if !ok {
		http.NotFound(w, r)
		return
	}

	if url, ok := GetCache(slug); ok {

		http.Redirect(w, r, url, http.StatusFound)

		return
	}

	url, err := ResolveYoutube(ch)

	if err != nil {

		http.Error(w, err.Error(), 500)

		return
	}

	SetCache(slug, url)

	http.Redirect(w, r, url, http.StatusFound)

}

func main() {

	http.HandleFunc("/live/", LiveHandler)

	log.Println("Server başladı :8080")

	log.Fatal(http.ListenAndServe(ListenAddr, nil))

}

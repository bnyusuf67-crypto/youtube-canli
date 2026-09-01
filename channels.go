package main

type Channel struct {
	Slug  string
	Name  string
	URL   string
	Group string
}

var Channels = map[string]Channel{

	"trthaber": {
		Slug:  "trthaber",
		Name:  "TRT Haber",
		URL:   "https://www.youtube.com/@trthaber/live",
		Group: "Haber",
	},

	"cnnturk": {
		Slug:  "cnnturk",
		Name:  "CNN Türk",
		URL:   "https://www.youtube.com/@cnnturk/live",
		Group: "Haber",
	},

	"ntv": {
		Slug:  "ntv",
		Name:  "NTV",
		URL:   "https://www.youtube.com/@ntv/live",
		Group: "Haber",
	},

	"ahaber": {
		Slug:  "ahaber",
		Name:  "A Haber",
		URL:   "https://www.youtube.com/@Ahaber/live",
		Group: "Haber",
	},

	"haberturk": {
		Slug:  "haberturk",
		Name:  "Habertürk",
		URL:   "https://www.youtube.com/@haberturktv/live",
		Group: "Haber",
	},

	"halktv": {
		Slug:  "halktv",
		Name:  "Halk TV",
		URL:   "https://www.youtube.com/@Halktvkanali/live",
		Group: "Haber",
	},

	"sozcutelevizyonu": {
		Slug:  "sozcutelevizyonu",
		Name:  "Sözcü TV",
		URL:   "https://m.youtube.com/watch?v=ztmY_cCtUl0",
		Group: "Haber",
	},

	"tgrthaber": {
		Slug:  "tgrthaber",
		Name:  "TGRT Haber",
		URL:   "https://www.youtube.com/@tgrthaber/live",
		Group: "Haber",
	},

	"flashhaber": {
		Slug:  "flashhaber",
		Name:  "Flash Haber",
		URL:   "https://www.youtube.com/@flashhabertv/live",
		Group: "Haber",
	},

	"haberglobal": {
		Slug:  "haberglobal",
		Name:  "Haber Global",
		URL:   "https://www.youtube.com/@haberglobal/live",
		Group: "Haber",
	},

	"tv100": {
		Slug:  "tv100",
		Name:  "TV100",
		URL:   "https://www.youtube.com/@tv100/live",
		Group: "Haber",
	},

	"bloomberght": {
		Slug:  "bloomberght",
		Name:  "Bloomberg HT",
		URL:   "https://www.youtube.com/@bloomberght/live",
		Group: "Ekonomi",
	},

	"benguturk": {
		Slug:  "benguturk",
		Name:  "Bengü Türk",
		URL:   "https://www.youtube.com/@tvbenguturk/live",
		Group: "Haber",
	},

	"krttv": {
		Slug:  "krttv",
		Name:  "KRT TV",
		URL:   "https://www.youtube.com/@krtcanli/live",
		Group: "Haber",
	},

	"ulusalkanal": {
		Slug:  "ulusalkanal",
		Name:  "Ulusal Kanal",
		URL:   "https://www.youtube.com/@ulusalkanaltv/live",
		Group: "Haber",
	},

	"ulketv": {
		Slug:  "ulketv",
		Name:  "Ülke TV",
		URL:   "https://www.youtube.com/@ulketv/live",
		Group: "Haber",
	},

	"ekoturk": {
		Slug:  "ekoturk",
		Name:  "EkoTürk",
		URL:   "https://www.youtube.com/@ekoturktv/live",
		Group: "Ekonomi",
	},

	"tv24": {
		Slug:  "tv24",
		Name:  "24 TV",
		URL:   "https://www.youtube.com/@YirmidortTV/live",
		Group: "Haber",
	},

	"aspor": {
		Slug:  "aspor",
		Name:  "A Spor",
		URL:   "https://www.youtube.com/@aspor/live",
		Group: "Spor",
	},

	"htspor": {
		Slug:  "htspor",
		Name:  "HT Spor",
		URL:   "https://www.youtube.com/@htspor/live",
		Group: "Spor",
	},

	"tvnet": {
		Slug:  "tvnet",
		Name:  "TV Net",
		URL:   "https://www.youtube.com/@tvnet/live",
		Group: "Haber",
	},

	"beinsportshaber": {
		Slug:  "beinsportshaber",
		Name:  "beIN Sports Haber",
		URL:   "https://www.youtube.com/@beINSPORTSTurkiye/live",
		Group: "Spor",
	},

	"cnbce": {
		Slug:  "cnbce",
		Name:  "CNBC-e",
		URL:   "https://www.youtube.com/@cnbce/live",
		Group: "Ekonomi",
	},
}

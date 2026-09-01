package main

import (
	"context"
	"errors"
	"os/exec"
	"strings"
)

func ResolveYoutube(channel Channel) (string, error) {

	ctx, cancel := context.WithTimeout(context.Background(), YTTimeout)
	defer cancel()

	cmd := exec.CommandContext(
		ctx,
		YTDLPCommand,
		"--geo-bypass",
		"--no-warnings",
		"-f",
		"best",
		"-g",
		channel.URL,
	)

	out, err := cmd.Output()

	if err != nil {
		return "", err
	}

	url := strings.TrimSpace(string(out))

	if !strings.HasPrefix(url, "http") {
		return "", errors.New("invalid youtube url")
	}

	return url, nil
}

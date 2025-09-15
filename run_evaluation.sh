#!/bin/bash

cp .env.example .env
docker compose up --abort-on-container-exit
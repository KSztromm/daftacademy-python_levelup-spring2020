from fastapi import FastAPI, Request, HTTPException, status, Response, Cookie, Depends
from pydantic import BaseModel
from typing import Dict
from hashlib import sha256
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasicCredentials, HTTPBasic
import secrets
import aiosqlite

app = FastAPI()


@app.on_event("startup")
async def startup():
    app.db_connection = await aiosqlite.connect('chinook.db')

@app.on_event("shutdown")
async def shutdown():
    await app.db_connection.close()

@app.get("/tracks")
async def tracks(page: int = 0, per_page: int = 10):
    app.db_connection.row_factory = aiosqlite.Row
    cursor = await app.db_connection.execute("SELECT * FROM tracks ORDER BY TrackId LIMIT :per_page OFFSET :per_page*:page",
        {'page': page, 'per_page': per_page})
    tracks = await cursor.fetchall()
    return tracks

@app.get("/tracks/composers")
async def tracks_composers(response: Response, composer_name: str):
    app.db_connection.row_factory = lambda cursor, x: x[0]
    cursor = await app.db_connection.execute("SELECT Name FROM tracks WHERE Composer = ? ORDER BY Name",
        (composer_name, ))
    tracks = await cursor.fetchall()
    if len(tracks) == 0:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"detail":{"error":"Composer not found"}}
    return tracks

class Album(BaseModel):
    title: str
    artist_id: int

@app.post("/albums")
async def new_album(response: Response, album: Album):
    app.db_connection.row_factory = None
    cursor = await app.db_connection.execute("SELECT ArtistId FROM artists WHERE ArtistId = ?",
        (album.artist_id, ))
    result = await cursor.fetchone()
    if result is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"detail":{"error":"Artist not found."}}
    cursor = await app.db_connection.execute("INSERT INTO albums (Title, ArtistId) VALUES (?, ?)",
        (album.title, album.artist_id))
    await app.db_connection.commit()
    response.status_code = status.HTTP_201_CREATED
    return {"AlbumId": cursor.lastrowid, "Title": album.title, "ArtistId": album.artist_id}
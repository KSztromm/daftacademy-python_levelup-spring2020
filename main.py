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

@app.get("/albums/{album_id}")
async def get_album(response: Response, album_id: int):
    app.db_connection.row_factory = aiosqlite.Row
    cursor = await app.db_connection.execute("SELECT * FROM albums WHERE AlbumId = ?",
        (album_id, ))
    album = await cursor.fetchone()
    return album

class Customer(BaseModel):
    company: str = None
    address: str = None
    city: str = None
    state: str = None
    country: str = None
    postalcode: str = None
    fax: str = None

@app.put("/customers/{customer_id}")
async def insert_customer(response: Response, customer_id: int, customer: Customer):
    cursor = await app.db_connection.execute("SELECT CustomerId FROM customers WHERE CustomerId = ?",
        (customer_id, ))
    result = await cursor.fetchone()
    if result is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"detail":{"error":"Customer not found"}}
    upd_cust = customer.dict(exclude_unset=True)
    values = list(upd_cust.values())
    if len(values) != 0:
        values.append(customer_id)
        query = "UPDATE customers SET "
        for key, value in upd_cust.items():
            key.capitalize()
            if key == "Postalcode":
                key = "PostalCode"
            query += f"{key}=?, "
        query = query[:-2]
        query += " WHERE CustomerId = ?"
        cursor = await app.db_connection.execute(query, tuple(values))
        await app.db_connection.commit()
    app.db_connection.row_factory = aiosqlite.Row
    cursor = await app.db_connection.execute("SELECT * FROM customers WHERE CustomerId = ?",
        (customer_id, ))
    customer = await cursor.fetchone()
    return customer

@app.get("/sales")
async def sales(response: Response, category: str):
    if category == "customers":
        app.db_connection.row_factory = aiosqlite.Row
        cursor = await app.db_connection.execute(
            "SELECT invoices.CustomerId, Email, Phone, ROUND(SUM(Total), 2) AS Sum "
            "FROM invoices JOIN customers on invoices.CustomerId = customers.CustomerId "
            "GROUP BY invoices.CustomerId ORDER BY Sum DESC, invoices.CustomerId")
        sales_st = await cursor.fetchall()
        return sales_st
    if category == "genres":
        app.db_connection.row_factory = aiosqlite.Row
        cursor = await app.db_connection.execute(
            "SELECT genres.Name, SUM(Quantity) AS Sum FROM invoice_items "
            "JOIN tracks ON invoice_items.TrackId = tracks.TrackId "
            "JOIN genres ON tracks.GenreId = genres.GenreId "
            "GROUP BY tracks.GenreId ORDER BY Sum DESC, genres.Name")
        sales_st = await cursor.fetchall()
        return sales_st
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"detail":{"error":"Category not found"}}
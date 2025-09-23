"use client"

import { useEffect, useState } from "react"


export function FallingBooksAnimation() {
  const [books, setBooks] = useState([])


  const bookEmojis = ["📚", "📖", "📕", "📗", "📘", "📙", "📔", "📒", "📓"]


  useEffect(() => {
    // Initialize books
    const initialBooks = []
    for (let i = 0; i < 15; i++) {
      initialBooks.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * -100,
        rotation: Math.random() * 360,
        speed: Math.random() * 2 + 1,
        size: Math.random() * 20 + 20,
        emoji: bookEmojis[Math.floor(Math.random() * bookEmojis.length)],
      })
    }
    setBooks(initialBooks)


    const interval = setInterval(() => {
      setBooks((prevBooks) =>
        prevBooks.map((book) => {
          let newY = book.y + book.speed
          const newRotation = book.rotation + 2


          // Reset book when it goes off screen
          if (newY > 110) {
            newY = Math.random() * -20 - 10
            return {
              ...book,
              y: newY,
              x: Math.random() * 100,
              rotation: newRotation,
              speed: Math.random() * 2 + 1,
              size: Math.random() * 20 + 20,
              emoji: bookEmojis[Math.floor(Math.random() * bookEmojis.length)],
            }
          }


          return {
            ...book,
            y: newY,
            rotation: newRotation,
          }
        }),
      )
    }, 50)


    return () => clearInterval(interval)
  }, [])


  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden opacity-20">
      {books.map((book) => (
        <div
          key={book.id}
          className="absolute text-primary transition-transform duration-75 ease-linear"
          style={{
            left: `${book.x}%`,
            top: `${book.y}%`,
            transform: `rotate(${book.rotation}deg)`,
            fontSize: `${book.size}px`,
          }}
        >
          {book.emoji}
        </div>
      ))}
    </div>
  )
}

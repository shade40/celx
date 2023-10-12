package main

import (
	"log"
	"net/http"
	"text/template"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

type Context struct {
	Page  string
	Pages []string
}

type Server struct {
	Pages []string
}

func (server Server) Home(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/xml")

	templates, err := template.ParseFiles(
		"templates/layout.tmpl",
		"templates/home.tmpl",
		"templates/components.tmpl",
	)

	if err != nil {
		log.Panic(err)
		return
	}

	context := Context{"home", server.Pages}
	templates.Execute(w, context)
}

func (server Server) Blog(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/xml")

	templates, err := template.ParseFiles(
		"templates/layout.tmpl",
		"templates/blog.tmpl",
	)

	if err != nil {
		log.Panic(err)
		return
	}

	context := Context{"blog", server.Pages}
	templates.Execute(w, context)
}

func (server Server) Buttons(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/xml")

	templates, err := template.ParseFiles(
		"templates/layout.tmpl",
		"templates/buttons.tmpl",
		"templates/components.tmpl",
	)

	if err != nil {
		log.Panic(err)
		return
	}

	context := Context{"buttons", server.Pages}
	templates.Execute(w, context)
}

func main() {
	server := Server{
		[]string{"", "blog"},
	}

	r := chi.NewRouter()
	r.Use(middleware.Logger)

	fs := http.FileServer(http.Dir("static"))
	r.Handle("/static/*", http.StripPrefix("/static/", fs))

	r.Get("/", server.Home)
	r.Get("/blog", server.Blog)

	http.ListenAndServe(":8080", r)
}

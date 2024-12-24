package main

import (
	"encoding/json"
	"fmt"
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

func (server Server) Shrink(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/xml")

	templates, err := template.ParseFiles(
		"templates/layout.tmpl",
		"templates/shrink.tmpl",
	)

	if err != nil {
		log.Panic(err)
		return
	}

	context := Context{"shrink", server.Pages}
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

func (server Server) PostPrompt(w http.ResponseWriter, r *http.Request) {
	var obj interface{}

	if err := json.NewDecoder(r.Body).Decode(&obj); err != nil {
		log.Panic(err)
	}

	indent, err := json.MarshalIndent(obj, "", "  ")

	if err != nil {
		log.Panic(err)
	}

	fmt.Fprintf(w, "<text eid='data' groups='w-fill h-fill'>%v\n</text>", string(indent))
}

func (server Server) Container(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/xml")

	templates, err := template.ParseFiles(
		"templates/layout.tmpl",
		"templates/container.tmpl",
		"templates/components.tmpl",
	)

	if err != nil {
		log.Panic(err)
		return
	}

	context := Context{"container", server.Pages}
	templates.Execute(w, context)
}

func main() {
	server := Server{
		[]string{"", "blog", "shrink", "container"},
	}

	r := chi.NewRouter()
	r.Use(middleware.Logger)

	fs := http.FileServer(http.Dir("static"))
	r.Handle("/static/*", http.StripPrefix("/static/", fs))

	r.Get("/", server.Home)
	r.Get("/container", server.Container)
	r.Get("/blog", server.Blog)
	r.Get("/shrink", server.Shrink)
	r.Post("/prompt", server.PostPrompt)

	http.ListenAndServe(":6900", r)
}

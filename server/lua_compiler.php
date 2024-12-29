<head>
    <script src="htmx.js"></script>
</head>
<body>
    <style>
        @font-face {
            font-family: "TX-02 Retina SemiCondensed";
            src: url("/TX-02-Retina-SemiCondensed.woff2");
        }

        * {
            margin: 0;
            border: none;
        }

        .row {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            width: 100%;
            height: 100%;
        }

        .row * {
            background-color: #101010;
            color: #cccccc;
            font-family: "TX-02 Retina SemiCondensed";
        }

        form {
            position: relative;
        }

        form button {
            position: absolute;
            bottom: 20px;
            right: 20px;
        }
    
        textarea {
            font-size: 18px;
            border-right: 1px solid grey;
        }

        pre {
            font-size: 18px;
        }
    </style>
    <form>
        <button hx-post="/lua" hx-target="#output">Execute</button>
        <div class="row">
            <textarea name="content" class="code"></textarea>
            <pre id="output">
            </pre>
        </div>
    </form>
</body>


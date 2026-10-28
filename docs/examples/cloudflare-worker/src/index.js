export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname !== "/hello") {
      return new Response("Not found", { status: 404 });
    }

    const name = url.searchParams.get("name");
    return Response.json({ message: `Hello, ${name.toUpperCase()}!` });
  },
};

/*
 * Simplified globbing functions. The code doesn't try to cover
 * all aspects of globbing, but it makes an attempt to cover enough
 * of it so that most users won't notice the difference.
 *
 * Try to do globbing without memory problems.
 *
 * Olaf Kirch <okir@caldera.de>
 */
#include <sys/stat.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <dirent.h>
#include <unistd.h>
#include <assert.h>
#include <pwd.h>

#define ASSERT(__p)	assert(__p)

#ifndef TEST
#include "config.h"
#include "proto.h"
#define ftpglob_char_p	char *
#define DEBUG(x)	do { } while (0)
#else
extern void		blkfree(char **);
#define ftpglob_char_p	const char *
static void		fatal(const char *msg);
#define DEBUG(x)	printf x
#endif

#define GLOBCHARS	"{[*?"
#define MAXGLOBS	120
#define MAXNEST		16

#define LEFTCURLY	'{'
#define RIGHTCURLY	'}'
#define LEFTBLOCKY	'['
#define RIGHTBLOCKY	']'
#define COMMA		','

/*
 * This holds information about the path name
 * we're currently looking at.
 */
struct dirbuf {
	char *		base;
	char *		tail;
	char *		end;
};

char *			globerr;
static char **		globbed;
static int		globcnt;

/*
 * Other wu-ftpd related stuff that should really be defined somewhere else
 */
char *			home;

/*
 * Locally used functions
 */
static void	globzap(void);
static int	doglob(struct dirbuf *, const char *);
static int	matchdir(struct dirbuf *, const char *);
static int	matchfile(struct dirbuf *, const char *, const char *);
static int	dobraces(struct dirbuf *, const char *, const char *);
static char *	gethomedir(const char **);
static void	remember(const char *);

static void	dirbuf_init(struct dirbuf *, const char *, unsigned int);
static int	dirbuf_addslash(struct dirbuf *);
static int	dirbuf_appendc(struct dirbuf *, char);
static int	dirbuf_appends(struct dirbuf *, const char *, unsigned int);
static const char *dirbuf_name(struct dirbuf *);
static const char *dirbuf_as_path(struct dirbuf *);
static void	dirbuf_destroy(struct dirbuf *);

char **
ftpglob(ftpglob_char_p pattern)
{
	struct dirbuf	namebuf;
	char		*basedir;

	globerr = NULL;
	globbed = NULL;
	globcnt = 0;

	basedir = "";
	if (pattern[0] == '~') {
		pattern++;
		if (!(basedir = gethomedir((const char **) &pattern))) {
			globerr = "Globbing failed";
			return NULL;
		}
	} else if (pattern[0] == '/') {
		basedir = "/";
		pattern++;
	}

	/* Initialize name buffer */
	dirbuf_init(&namebuf, basedir, 1024);

	if (!doglob(&namebuf, pattern) || !globcnt) {
		if (!globerr)
			globerr = "Globbing failed";
		globzap();
	}

	dirbuf_destroy(&namebuf);

	return globbed;
}

static void
globzap(void)
{
	if (globbed) {
		blkfree(globbed);
		free(globbed);
	}
	globbed = NULL;
	globcnt = 0;
}

static int
doglob(struct dirbuf *np, const char *pattern)
{
	struct dirbuf	name = *np;
	struct stat	stb;
	const char	*s;


	/* Loop over all pattern components */
	while (*pattern) {
		/* Skip slashes, but make sure the named file
		 * exists and is a directory.
		 * This takes care of "foobar/" patterns
		 */
		if (*pattern == '/' || !strncmp(pattern, "./", 2)) {
			if (stat(dirbuf_as_path(&name), &stb) < 0
			 || !S_ISDIR(stb.st_mode))
				return 0;
			pattern++;
			continue;
		}

		/* Try to match a component of the path name */
		for (s = pattern; *s && *s != '/'; s++) {
			/* Remainder has globbing chars */
			if (strchr(GLOBCHARS, *s))
				return matchdir(&name, pattern);
		}

		/* This path component didn't contain a special
		 * character, so no matching required.
		 * Make sure though that the file exists. */
		if (!dirbuf_addslash(&name)
		 || !dirbuf_appends(&name, pattern, s - pattern)
		 || access(dirbuf_as_path(&name), F_OK) < 0)
			return 0;
		pattern = s;
	}

	remember(dirbuf_as_path(&name));
	return 1;
}

static int
matchdir(struct dirbuf *np, const char *pattern)
{
	struct dirbuf	name = *np;
	DIR		*dir;
	struct dirent	*dp;
	int		nmatches = 0;

	/* If path is not empty, append a path separator */
	if (!dirbuf_addslash(&name))
		return 0;

	if (!(dir = opendir(dirbuf_as_path(&name))))
		return 0;

	while ((dp = readdir(dir)) != NULL) {
		if (dp->d_name[0] == '.' && pattern[0] != '.')
			continue;
		DEBUG(("* matching \"%s\"\n", dp->d_name));
		if (matchfile(&name, dp->d_name, pattern))
			nmatches++;
	}
	closedir(dir);
	return nmatches;
}

static int
matchfile(struct dirbuf *np, const char *fname, const char *pattern)
{
	struct dirbuf	name = *np;
	unsigned char	pc, fc;

	/* DEBUG(("* try \"%s\" ~ \"%s\"\n", fname, pattern)); */
	while (*pattern && *pattern != '/') {
		pc = *pattern++;
		fc = *fname;
		switch (pc) {
		case '?':
			if (!fc || !dirbuf_appendc(&name, fc))
				return 0;
			fname++;
			break;

		/* Match 0 or more characters. Try to match greedily
		 * i.e. as many characters as possible. */
		case '*': {
			struct dirbuf	temp;
			unsigned int	n, ok = 0;

			n = strlen(fname);
			do {
				temp = name;
				if (dirbuf_appends(&temp, fname, n)) {
					ok = matchfile(&temp, fname + n,
							pattern);
				}
			} while (!ok && n--);

			return ok;
			}

		/* Match character range */
		case LEFTBLOCKY: {
			unsigned char	from, to;
			int		ok = 0;

			if (fc == '\0')
				return 0;
			while (1) {
				to = from = *pattern++;
				if (from == RIGHTBLOCKY)
					break;
				if (from == '\0')
					return 0;

				if (*pattern == '-') {
					pattern++;
					to = *pattern++;
					if (to == '\0')
						return 0;
				}
				if (from <= fc && fc <= to)
					ok = 1;
			}
			if (!ok || !dirbuf_appendc(&name, fc))
				return 0;
			fname++;
			break;
			}

		case LEFTCURLY:
			/* Handle braces - icky ugly and bad */
			return dobraces(&name, fname, pattern);

		case '\\':
			if ((fc = *++fname) == '\0')
				return 0;
			/* fallthru */
		default:
			if (pc != fc || !dirbuf_appendc(&name, fc))
				return 0;
			fname++;
			break;
		}
	}

	/* Pattern exhausted - make sure we've matched the full
	 * filename! */
	if (*fname != '\0')
		return 0;

	return doglob(&name, pattern);
}

/*
 * This one deals with the expansion of {...} expressions.
 * This is complicated by nesting ([...] and {...} can occur
 * within).
 *
 * We do this in two passes. If the pattern is
 * 	{alt1,alt2,...,altN}rest
 * then we first go over the pattern finding "rest". Once we have
 * it, we make a second pass, this time matching the given filename
 * against "altK" concatenated with "rest" for each alternative "altK".
 */
static int
dobraces(struct dirbuf *np, const char *fname, const char *pattern)
{
	const char	*begin, *tail = NULL;
	char		patbuf[1024], stack[MAXNEST], pc;
	unsigned int	nc, match = 0, nsp = 0;

	if (strlen(pattern) >= sizeof(patbuf))
		return 0;

	/* Remember where our pattern begins */
	begin = pattern;

again:
	/* We've scanned past the opening brace, but it's there,
	 * so count it */
	stack[0] = RIGHTCURLY;
	nsp = 1;
	nc = 0;

	while (*pattern) {
		pc = *pattern++;

		/* Do we have a complete alternative? */
		if (nsp == 1 && (pc == COMMA || pc == RIGHTCURLY)) {
			if (tail != NULL) {
				struct dirbuf	name = *np;

				ASSERT(nc+strlen(tail) < sizeof(patbuf));
				patbuf[nc] = '\0';
				strcat(patbuf, tail);
				if (matchfile(&name, fname, patbuf))
					match++;
			}
			/* Have we closed the outermost bracket? */
			if (pc == RIGHTCURLY) {
				nsp--;
				break;
			}
			/* Start scanning for the next alternative */
			nc = 0;
			continue;
		}

		/* Nested character classes/alternatives */
		if (pc == LEFTCURLY || pc == LEFTBLOCKY) {
			if (nsp >= MAXNEST)
				return 0;
			stack[nsp++] = (pc == LEFTCURLY)?
					RIGHTCURLY : RIGHTBLOCKY;
		} else
		if (pc == RIGHTCURLY || pc == RIGHTBLOCKY) {
			/* Make sure closing bracket/brace
			 * matches opening one */
			if (!nsp || stack[--nsp] != pc)
				return 0;
		}

		/* Copy to pattern buffer */
		ASSERT(nc < sizeof(patbuf)-2);
		patbuf[nc++] = pc;
		patbuf[nc] = '\0';
	}

	/* No closing brace? Trouble. */
	if (nsp != 0)
		return 0;

	if (tail == NULL) {
		/* We have the remainder. Keep it and start over */
		tail = pattern;
		pattern = begin;
		goto again;
	}

	return match;
}

static void
dirbuf_init(struct dirbuf *np, const char *name, unsigned int size)
{
	unsigned int	n;

	memset(np, 0, sizeof(*np));
	if ((n = strlen(name)) + 1 > size)
		size = n + 1;
	np->base = (char *) malloc(size);
	np->tail = np->base + n;
	np->end  = np->base + size - 1;
	strcpy(np->base, name);
}

/*
 * Special case - avoid adjacent slashes, and do not add a slash
 * if the path is empty
 */
static int
dirbuf_addslash(struct dirbuf *np)
{
	if (np->tail == np->base ||  np->tail[-1] == '/')
		return 1;
	return dirbuf_appends(np, "/", 1);
}

static int
dirbuf_appendc(struct dirbuf *np, char c)
{
	ASSERT(c != 0);
	return dirbuf_appends(np, &c, 1);
}

static int
dirbuf_appends(struct dirbuf *np, const char *s, unsigned int n)
{
	if (np->tail + n >= np->end)
		return 0;
	memcpy(np->tail, s, n);
	np->tail += n;
	return 1;
}

static const char *
dirbuf_name(struct dirbuf *np)
{
	np->tail[0] = '\0';
	return np->base;
}

static const char *
dirbuf_as_path(struct dirbuf *np)
{
	if (np->base == np->tail)
		return ".";
	return dirbuf_name(np);
}

static void
dirbuf_destroy(struct dirbuf *np)
{
	free(np->base);
	memset(np, 0, sizeof(*np));
}

static char *
gethomedir(const char **patternp)
{
	static char	userhome[1024];
	unsigned int	len;
	const char	*p;
	char		username[128];
	struct passwd	*pw;

	p = *patternp;
	if (*p == '/' || *p == '\0')
		return home;

	if ((len = strcspn(p, "/")) >= sizeof(username)-1)
		return NULL;
	*patternp = p + len;
	memcpy(username, p, len);
	username[len] = '\0';

	if ((pw = getpwnam(username)) == NULL)
		return NULL;
	if (!pw->pw_dir || !pw->pw_dir[0])
		return "/";

	if ((len = strlen(pw->pw_dir)) >= sizeof(userhome) - 1)
		return NULL;
	strcpy(userhome, pw->pw_dir);
	userhome[len] = '\0';
	return userhome;
}

static void
remember(const char *s)
{
	char	**p, *str;

	DEBUG(("* accepted \"%s\"\n", s));
	if (globcnt >= MAXGLOBS)
		return;
	if ((globcnt & 15) == 0) {
		p = (char **) realloc(globbed,
				(globcnt + 17) * sizeof(char *));
		if (p == NULL)
			fatal("out of memory");
		globbed = p;
	}
	if ((str = strdup(s)) == NULL)
		fatal("out of memory");
	globbed[globcnt++] = str;
	globbed[globcnt] = NULL;
}

/*
 * Miscellaneous functions not needed here, but provided
 * for wu-ftpd compatibility
 */
char **
blkcpy(char **dst, char **src)
{
	unsigned int	n;

	for (n = 0; src[n]; n++)
		dst[n] = src[n];
	dst[n] = NULL;
	return dst;
}

void
blkfree(char **p)
{
	for (; *p; p++)
		free(*p);
}

char **
copyblk(register char **src)
{
	unsigned int	n;
	char		**dst;
	
	for (n = 0; src[n]; n++)
		;
	if (!(dst = (char **) malloc((n + 1) * sizeof(char *))))
		fatal("Out of memory");
	return blkcpy(dst, src);
}

char *
strspl(char *cp, char *dp)
{
	char	*ep;

	if (!(ep = (char *) malloc(strlen(cp) + strlen(dp) + 1)))
		fatal("Out of memory");
	strcpy(ep, cp);
	strcat(ep, dp);
	return ep;
}

#ifdef TEST
int
main(int argc, char **argv)
{
	char	**res, **p;

	argc--, argv++;
	while (argc--)  {
		printf("%s\n", *argv);
		res = ftpglob(*argv++);
		if (res == 0) {
			printf("=> %s\n", globerr);
			continue;
		}
		for (p = res; *p; p++) {
			printf("  %s\n", *p);
			free(*p);
		}
		free(res);
	}
	return 0;
}

static void
fatal(const char *msg)
{
	printf("Fatal error: %s\n", msg);
	exit(1);
}
#endif

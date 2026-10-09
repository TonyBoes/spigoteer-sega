FROM node:22-trixie

ARG TZ
ENV TZ="$TZ"

ARG CLAUDE_CODE_VERSION=latest

# Install basic development tools and iptables/ipset
RUN apt-get update && apt-get install -y --no-install-recommends \
  less \
  git \
  procps \
  sudo \
  fzf \
  zsh \
  man-db \
  unzip \
  gnupg2 \
  gh \
  iptables \
  ipset \
  iproute2 \
  dnsutils \
  aggregate \
  jq \
  nano \
  vim \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure default node user has access to /usr/local/share
RUN mkdir -p /usr/local/share/npm-global && \
  chown -R node:node /usr/local/share

ARG USERNAME=node

# Persist bash history.
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  && mkdir /commandhistory \
  && touch /commandhistory/.bash_history \
  && chown -R $USERNAME /commandhistory

# Set `DEVCONTAINER` environment variable to help with orientation
ENV DEVCONTAINER=true

# A UTF-8 locale that exists in the base image. Without it every shell prints
# `setlocale: LC_ALL: cannot change locale (en_US.UTF-8)`, because the host's
# LANG is forwarded but never generated here. C.UTF-8 needs no locale-gen.
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

# Create workspace and config directories and set permissions
RUN mkdir -p /workspace /home/node/.claude && \
  chown -R node:node /workspace /home/node/.claude

WORKDIR /workspace

ARG GIT_DELTA_VERSION=0.18.2
RUN ARCH=$(dpkg --print-architecture) && \
  wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  sudo dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

# Set up non-root user
USER node

# Install global packages
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin

# Set the default shell to zsh rather than sh
ENV SHELL=/bin/zsh

# Set the default editor and visual
ENV EDITOR=nano
ENV VISUAL=nano

# Default powerline10k theme
ARG ZSH_IN_DOCKER_VERSION=1.2.0
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \
  -p git \
  -p fzf \
  -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
  -a "source /usr/share/doc/fzf/examples/completion.zsh" \
  -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  -x

# Install Claude
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}


# uv - Python toolchain: interpreter versions, dependencies, virtualenvs.
# Pair with pypi.org and files.pythonhosted.org in firewall-extras.conf.
ARG UV_VERSION=0.10.8
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh
ENV PATH="/home/node/.local/bin:$PATH"

# Copy the firewall script and the per-project allowlist. Both live in the
# image rather than the bind-mounted workspace, so an agent in this container
# cannot edit the allowlist it is restricted by.
COPY init-firewall.sh firewall-extras.conf /usr/local/bin/
USER root

# NOTE: Claude Code's own /sandbox (bubblewrap) CANNOT work in this container.
# bubblewrap asserts at startup that it is either setuid root or holds no
# capabilities, and aborts otherwise. --cap-add=NET_ADMIN/NET_RAW, which
# init-firewall.sh requires, are granted as AMBIENT capabilities and are
# inherited by every process including bwrap:
#     bwrap: Unexpected capabilities but not setuid, old file caps config?
# They cannot be dropped from inside - capsh needs CAP_SETPCAP, which we do
# not have. Verified 2026-09-16; same failure without --cap-add works fine.
# See containers/bubblewrap#380 and #397 (both open since 2020).
#
# The iptables egress firewall is therefore the isolation layer, and
# bubblewrap, socat, @anthropic-ai/sandbox-runtime and a managed-settings.json
# declaring "sandbox.enabled" have been REMOVED - shipping them implies a
# capability this container does not have.

RUN chown root:root /usr/local/bin/init-firewall.sh /usr/local/bin/firewall-extras.conf && \
  chmod 0755 /usr/local/bin/init-firewall.sh && \
  chmod 0644 /usr/local/bin/firewall-extras.conf && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall && \
  chmod 0440 /etc/sudoers.d/node-firewall

# ---------------------------------------------------------------------------
# VARIANTS
#
# Sits inside the `USER root` section, after the firewall COPY/chown and
# before the final `USER node`, so the base layers stay cached when VARIANTS
# changes.
#
# VARIANTS is a space-separated list, so variants stack:
#     --build-arg VARIANTS="wordpress"
#     --build-arg VARIANTS="python wordpress"
#
# Each variant owns a directory under variants/ containing an install.sh, which
# is responsible for placing its own config and scripts. They run in the order
# given. Keep variants coarse and few - two that stack is fine, ten that must
# compose is a combinatorial testing problem nobody will actually do.
# ---------------------------------------------------------------------------
ARG VARIANTS=""

COPY variants/ /tmp/variants/

RUN set -eux; \
    for v in ${VARIANTS}; do \
      if [ ! -x "/tmp/variants/$v/install.sh" ]; then \
        echo "ERROR: unknown variant '$v'" >&2; exit 1; \
      fi; \
      echo "=== variant: $v ==="; \
      "/tmp/variants/$v/install.sh"; \
    done; \
    rm -rf /tmp/variants

# ---------------------------------------------------------------------------
# EXTRA_APT_PACKAGES
#
# Per-project Debian packages, space-separated, set from devcontainer.json:
#     "build": { "args": { "EXTRA_APT_PACKAGES": "chromium poppler-utils" } }
#
# This is how a project gets packages without editing its Dockerfile, so every
# project's Dockerfile stays byte-identical to the template and a template fix
# is a plain copy. Sits after VARIANTS so a project's list changing does not
# bust the shared layers. Build-time apt is not subject to the runtime firewall.
# ---------------------------------------------------------------------------
ARG EXTRA_APT_PACKAGES=""

RUN set -eux; \
    if [ -n "${EXTRA_APT_PACKAGES}" ]; then \
      echo "=== extra apt packages: ${EXTRA_APT_PACKAGES} ==="; \
      apt-get update; \
      apt-get install -y --no-install-recommends ${EXTRA_APT_PACKAGES}; \
      apt-get clean; rm -rf /var/lib/apt/lists/*; \
    fi

# Assertion: nothing root executes may be writable by node. node has NOPASSWD
# sudo for init-firewall.sh and, with the wordpress variant, wp-services. A
# writable copy of either is a privilege-escalation path - edit the script,
# run it as root. This fails the build rather than shipping it.
RUN set -eux; \
    for f in /usr/local/bin/init-firewall.sh /usr/local/bin/firewall-extras.conf \
             /usr/local/bin/wp-services; do \
      [ -e "$f" ] || continue; \
      owner="$(stat -c '%U' "$f")"; \
      perms="$(stat -c '%a' "$f")"; \
      [ "$owner" = "root" ] || { echo "ERROR: $f owned by $owner, not root" >&2; exit 1; }; \
      case "$perms" in *[2367]) echo "ERROR: $f group/other writable ($perms)" >&2; exit 1;; esac; \
    done; \
    echo "permission assertion passed"

USER node
